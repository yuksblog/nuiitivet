"""Reload journal: a pull-able record of recent hot-reload events (dev-only).

The dev bridge is AI-initiated: the assistant reads (``describe_tree`` /
``screenshot``) and acts (``click`` / ``type`` / ``key``) on its own turns, but
has no way to notice what changed *between* turns. In a pair session the human
edits and saves while the assistant is mid-task, so its cached ``describe_tree``
and its assumptions about the source both go stale. The most damaging case is a
**failed** reload: the human saves, it errors, the previous UI keeps running,
and the assistant -- unaware -- keeps operating against a tree that no longer
reflects the code it is reading.

This module records each reload the controller performs into a bounded ring
buffer, exposed as a perception surface the assistant pulls when it wants (see
``bridge.py``'s ``/reload_log`` and the ``reload_log`` MCP tool). An AI pair acts
in turns, not a continuous attention loop, and MCP is request/response -- so a
pull-able log is a natural fit alongside ``describe_tree`` / ``screenshot``,
letting the assistant detect "the code changed under me -- and did it even
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

# Default number of reload events retained. Small: an assistant only needs the
# recent tail to notice "the code changed under me since my last turn".
DEFAULT_CAPACITY = 50

# Upper bound on a recorded traceback, in characters. A failed reload's
# traceback is the same failure already surfaced on the console and app banner;
# the head carries the message and the innermost frames, which is what the
# assistant needs to reason about the break. Capped so a pathological traceback
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
        modules: Names of the user modules reloaded (success only; empty on
            error, since the reload did not complete). The reloader reloads *all*
            user modules on any change, so this alone does not say which file the
            human touched -- see ``changed``.
        changed: Names of the modules whose *source actually changed* since the
            previous reload, detected by content hash. An empty list means a
            no-op save (the file's mtime changed but its bytes did not, e.g. an
            editor autosave or formatter re-save): the assistant can skip
            re-reading. A non-empty list pinpoints exactly which file(s) the
            human edited, so a re-read can target them.
        error: The failure traceback (error only; ``None`` on success), capped.
    """

    seq: int
    timestamp: float
    outcome: str
    modules: tuple[str, ...]
    changed: tuple[str, ...]
    error: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict.

        ``modules`` and ``error`` are omitted when empty (their absence is itself
        the signal). ``changed`` is *always* present -- an empty ``changed`` is a
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
        payload["changed"] = list(self.changed)
        if self.error is not None:
            payload["error"] = self.error
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
        self, modules: Iterable[str], *, changed: Iterable[str] = ()
    ) -> ReloadEvent:
        """Record a successful reload and return the event.

        Args:
            modules: All user modules reloaded.
            changed: The subset whose source actually changed (empty for a no-op
                save).
        """
        return self._record(
            "success", modules=tuple(modules), changed=tuple(changed), error=None
        )

    def record_error(
        self, traceback_text: str, *, changed: Iterable[str] = ()
    ) -> ReloadEvent:
        """Record a failed reload carrying ``traceback_text`` and return the event."""
        return self._record(
            "error",
            modules=(),
            changed=tuple(changed),
            error=_truncate_traceback(traceback_text),
        )

    def _record(
        self,
        outcome: str,
        *,
        modules: tuple[str, ...],
        changed: tuple[str, ...],
        error: Optional[str],
    ) -> ReloadEvent:
        with self._lock:
            event = ReloadEvent(
                seq=next(self._seq),
                timestamp=time.time(),
                outcome=outcome,
                modules=modules,
                changed=changed,
                error=error,
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
