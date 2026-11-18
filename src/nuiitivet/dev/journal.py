"""Reload journal: a pull-able record of recent hot-reload events (dev-only).

The dev bridge is agent-initiated: the agent reads (``describe_tree`` /
``screenshot``) and acts (``click`` / ``type`` / ``key``) on its own turns, but
has no way to notice what changed *between* turns. In a pair session the human
edits and saves while the agent is mid-task, so its cached ``describe_tree``
and its assumptions about the source both go stale. The most damaging case is a
**failed** reload: the human saves, it errors, the previous UI keeps running,
and the agent -- unaware -- keeps operating against a tree that no longer
reflects the code it is reading.

This module records each reload the controller performs into a bounded ring
buffer, exposed as a perception surface the agent pulls when it wants (see
``bridge.py``'s ``/reload_log`` and the ``reload_log`` MCP tool). An agent acts
in turns, not a continuous attention loop, and MCP is request/response -- so a
pull-able log is a natural fit alongside ``describe_tree`` / ``screenshot``,
letting the agent detect "the code changed under me -- and did it even
compile?" and decide on its own to re-read files / re-``describe_tree`` before
acting.

Recording happens on the UI thread (the controller's clock-drain); reads happen
on HTTP worker threads, so the buffer is guarded by a lock.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from itertools import count
from typing import Any, Deque, Iterable, Optional

# Default number of reload events retained. Small: an agent only needs the
# recent tail to notice "the code changed under me since my last turn".
DEFAULT_CAPACITY = 50

# Upper bound on a recorded traceback, in characters. A failed reload's
# traceback is the same failure already surfaced on the console and app banner;
# the head carries the message and the innermost frames, which is what the
# agent needs to reason about the break. Capped so a pathological traceback
# can never dominate the response.
_TRACEBACK_CAP = 4000

# Marker appended when a traceback is truncated to the cap.
_TRUNCATION_MARKER = "\n... [traceback truncated]"


def _truncate_traceback(text: str, *, cap: int = _TRACEBACK_CAP) -> str:
    """Return ``text`` capped to ``cap`` characters, marking any truncation."""
    if len(text) <= cap:
        return text
    return text[:cap] + _TRUNCATION_MARKER


@dataclass(frozen=True)
class ReloadEvent:
    """One recorded hot-reload outcome.

    Attributes:
        seq: Monotonic id, unique and increasing across the app's lifetime. A
            client compares it against the last ``seq`` it saw to tell whether
            new reloads happened since its previous turn.
        timestamp: Unix time (seconds) when the event was recorded.
        outcome: ``"success"`` or ``"error"``.
        modules: Names of the user modules re-executed (success only; empty on
            error, since the reload did not complete): the modules edited
            outside def bodies, and the modules that import them.
        patched: Names of the user modules whose living functions took new code
            (success only): only def bodies were edited, and every object made
            from the module is still current.
        changed: Names of the modules whose *source actually changed* since the
            previous reload, detected by content hash. An empty list means a
            no-op save (the file's mtime changed but its bytes did not, e.g. an
            editor autosave or formatter re-save): the agent can skip
            re-reading. A non-empty list pinpoints exactly which file(s) the
            human edited, so a re-read can target them.
        error: The failure traceback (error only; ``None`` on success), capped.
        stale: Per class a re-executed module defined before, the number of its
            non-widget instances still alive. They run the old class, and only a
            restart updates them. On an error they are the likely cause unless
            the traceback points at the code just changed.
        inert_windows: Ids of open windows whose root is a widget instance, so
            no reload -- this one included -- can change their tree (success
            only). A window listed here needs its ``Window(content=...)``
            changed to a factory before edits can land.
    """

    seq: int
    timestamp: float
    outcome: str
    modules: tuple[str, ...]
    changed: tuple[str, ...]
    error: Optional[str]
    inert_windows: tuple[int, ...] = ()
    patched: tuple[str, ...] = ()
    stale: tuple[tuple[str, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict.

        ``modules``, ``patched``, ``stale`` and ``error`` are omitted when empty
        (their absence is itself the signal). ``changed`` is *always* present -- an empty ``changed`` is a
        positive signal (a no-op save), so it must be distinguishable from "not
        recorded".
        """
        payload: dict[str, Any] = {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "outcome": self.outcome,
        }
        if self.modules:
            payload["modules"] = list(self.modules)
        if self.patched:
            payload["patched"] = list(self.patched)
        if self.stale:
            payload["stale"] = dict(self.stale)
        payload["changed"] = list(self.changed)
        if self.error is not None:
            payload["error"] = self.error
        if self.inert_windows:
            payload["inert_windows"] = list(self.inert_windows)
        return payload


class ReloadJournal:
    """A thread-safe, bounded ring buffer of recent :class:`ReloadEvent`\\ s.

    The controller records into it on the UI thread; the bridge reads from it on
    HTTP worker threads. Both paths take the lock, so the buffer is safe to share
    without either side owning the other.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._events: Deque[ReloadEvent] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        # Monotonic sequence source. Starts at 1 so a client's "last seen seq"
        # sentinel of 0 means "I have seen nothing yet".
        self._seq = count(1)

    @property
    def capacity(self) -> int:
        """The maximum number of events retained."""
        return self._capacity

    def record_success(
        self,
        modules: Iterable[str],
        *,
        patched: Iterable[str] = (),
        changed: Iterable[str] = (),
        stale: Optional[dict[str, int]] = None,
        inert_windows: Iterable[int] = (),
    ) -> ReloadEvent:
        """Record a successful reload and return the event.

        Args:
            modules: The user modules re-executed.
            patched: The user modules whose living functions took new code.
            changed: The modules whose source actually changed (empty for a no-op
                save).
            stale: Old classes with instances still alive, and how many.
            inert_windows: Ids of windows whose instance root kept this reload
                from changing their tree.
        """
        return self._record(
            "success",
            modules=tuple(modules),
            changed=tuple(changed),
            error=None,
            inert_windows=tuple(inert_windows),
            patched=tuple(patched),
            stale=tuple(sorted((stale or {}).items())),
        )

    def record_error(
        self,
        traceback_text: str,
        *,
        changed: Iterable[str] = (),
        stale: Optional[dict[str, int]] = None,
    ) -> ReloadEvent:
        """Record a failed reload and return the event.

        Args:
            traceback_text: The failure traceback.
            changed: The modules whose source actually changed.
            stale: Old classes with instances still alive, and how many.
        """
        return self._record(
            "error",
            modules=(),
            changed=tuple(changed),
            error=_truncate_traceback(traceback_text),
            stale=tuple(sorted((stale or {}).items())),
        )

    def _record(
        self,
        outcome: str,
        *,
        modules: tuple[str, ...],
        changed: tuple[str, ...],
        error: Optional[str],
        inert_windows: tuple[int, ...] = (),
        patched: tuple[str, ...] = (),
        stale: tuple[tuple[str, int], ...] = (),
    ) -> ReloadEvent:
        with self._lock:
            event = ReloadEvent(
                seq=next(self._seq),
                timestamp=time.time(),
                outcome=outcome,
                modules=modules,
                changed=changed,
                error=error,
                inert_windows=inert_windows,
                patched=patched,
                stale=stale,
            )
            self._events.append(event)
            return event

    def recent(self, limit: Optional[int] = None) -> list[ReloadEvent]:
        """Return the most recent events, oldest-first.

        Args:
            limit: Maximum number of events to return (the newest ``limit``). A
                non-positive limit returns an empty list; ``None`` returns all
                retained events.
        """
        with self._lock:
            events = list(self._events)
        if limit is None:
            return events
        if limit <= 0:
            return []
        return events[-limit:]
