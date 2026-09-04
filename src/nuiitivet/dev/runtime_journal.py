"""Runtime journal: a pull-able record of the running app's log output and
uncaught exceptions (dev-only).

The dev bridge exposes what the assistant *sees* (``describe_tree`` /
``screenshot``) and what it and the human *did* (``reload_log`` /
``interaction_log``), but nothing surfaces what the running app *emitted*. When
an assistant-driven ``click`` / ``type`` / ``key`` makes a callback raise, the
framework swallows it (the app stays alive) and logs it -- to a console the
assistant, driving over MCP, cannot read. The post-action ``describe_tree`` then
shows an unchanged tree: the assistant can see *that* nothing happened, not
*why*.

This module is the missing surface. A :class:`RuntimeJournal` is a bounded ring
buffer of :class:`RuntimeEvent`\\ s -- one per captured ``logging`` record or
uncaught exception -- that the bridge serves at ``/runtime_log`` and the
``runtime_log`` MCP tool pulls. Each event carries a monotonic ``seq`` so the
assistant can tell what is new since its last turn, mirroring the reload and
interaction journals.

The journal itself holds no capture policy: it is a plain, thread-safe buffer
written from any thread (the UI thread's callback path, a background thread's
excepthook, an asyncio error logged from the loop) and read on HTTP worker
threads. De-duplication of repeated errors lives upstream at the emit sites
(``logging_once``); this buffer records whatever reaches it.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from itertools import count
from typing import Any, Deque, Optional

# Default number of runtime events retained. Larger than the reload journal: a
# single failing frame or a chatty background thread can emit a burst, and the
# assistant wants the recent tail intact rather than evicted by noise.
DEFAULT_CAPACITY = 200

# Upper bound on a recorded traceback, in characters. The head carries the
# exception message and the innermost frames -- what the assistant needs to
# reason about the failure -- so truncation keeps the front. Capped so one
# pathological traceback cannot dominate a response. Matches the reload journal.
_TRACEBACK_CAP = 4000

# Marker appended when a traceback is truncated to the cap.
_TRUNCATION_MARKER = "\n... [traceback truncated]"

# Upper bound on a single log message, in characters. A message is arbitrary
# app output; cap it so a giant one cannot bloat the buffer or a response.
_MESSAGE_CAP = 2000

# Marker appended when a message is truncated to the cap.
_MESSAGE_TRUNCATION_MARKER = "… [truncated]"


def _truncate(text: str, cap: int, marker: str) -> str:
    """Return ``text`` capped to ``cap`` characters, marking any truncation."""
    if len(text) <= cap:
        return text
    return text[:cap] + marker


@dataclass(frozen=True)
class RuntimeEvent:
    """One captured log record or uncaught exception from the running app.

    Attributes:
        seq: Monotonic id, unique and increasing across the app's lifetime. A
            client compares it against the last ``seq`` it saw to tell whether
            new events happened since its previous turn.
        timestamp: Unix time (seconds) when the event was recorded.
        level: Severity name -- a ``logging`` level (``"WARNING"`` / ``"ERROR"``
            / ``"CRITICAL"``) for captured records, or ``"ERROR"`` for an
            uncaught exception.
        source: Where the event was captured: ``"logging"`` (a ``logging``
            record), ``"thread"`` (a background thread's uncaught exception), or
            ``"excepthook"`` (the main thread's uncaught exception).
        thread: Name of the thread the event originated on, so the assistant can
            tell a UI-thread failure from a background one.
        message: The log message (or the exception's ``str``), length-capped.
        logger: The ``logging`` logger name for a ``"logging"`` event; ``None``
            for an excepthook capture.
        exc_type: The exception class name when the event carries one; ``None``
            for a plain log record without ``exc_info``.
        traceback: The formatted traceback when present, capped; ``None`` for a
            plain log record without one.
    """

    seq: int
    timestamp: float
    level: str
    source: str
    thread: str
    message: str
    logger: Optional[str] = None
    exc_type: Optional[str] = None
    traceback: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict, omitting fields that do not apply.

        ``logger`` / ``exc_type`` / ``traceback`` are omitted when absent so each
        event reads as exactly what was captured -- a bare warning carries none
        of them, an uncaught exception carries the latter two.
        """
        payload: dict[str, Any] = {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "level": self.level,
            "source": self.source,
            "thread": self.thread,
            "message": self.message,
        }
        if self.logger is not None:
            payload["logger"] = self.logger
        if self.exc_type is not None:
            payload["exc_type"] = self.exc_type
        if self.traceback is not None:
            payload["traceback"] = self.traceback
        return payload


class RuntimeJournal:
    """A thread-safe, bounded ring buffer of recent :class:`RuntimeEvent`\\ s.

    Capture surfaces append from whatever thread produced the event; the bridge
    reads on HTTP worker threads. Both paths take the lock, so the buffer is safe
    to share without either side owning the other. Mirrors
    :class:`~nuiitivet.dev.journal.ReloadJournal`.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._events: Deque[RuntimeEvent] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        # Monotonic sequence source. Starts at 1 so a client's "last seen seq"
        # sentinel of 0 means "I have seen nothing yet".
        self._seq = count(1)

    @property
    def capacity(self) -> int:
        """The maximum number of events retained."""
        return self._capacity

    def record(
        self,
        *,
        level: str,
        source: str,
        thread: str,
        message: str,
        logger: Optional[str] = None,
        exc_type: Optional[str] = None,
        traceback: Optional[str] = None,
    ) -> RuntimeEvent:
        """Record one event and return it.

        ``message`` and ``traceback`` are length-capped here so callers need not
        pre-truncate. Thread-safe.
        """
        capped_message = _truncate(message, _MESSAGE_CAP, _MESSAGE_TRUNCATION_MARKER)
        capped_tb = (
            _truncate(traceback, _TRACEBACK_CAP, _TRUNCATION_MARKER)
            if traceback is not None
            else None
        )
        with self._lock:
            event = RuntimeEvent(
                seq=next(self._seq),
                timestamp=time.time(),
                level=level,
                source=source,
                thread=thread,
                message=capped_message,
                logger=logger,
                exc_type=exc_type,
                traceback=capped_tb,
            )
            self._events.append(event)
            return event

    def recent(self, limit: Optional[int] = None) -> list[RuntimeEvent]:
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


__all__ = [
    "DEFAULT_CAPACITY",
    "RuntimeEvent",
    "RuntimeJournal",
]
