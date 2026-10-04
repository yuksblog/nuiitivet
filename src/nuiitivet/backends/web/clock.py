"""The clock of the browser backend."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, List, Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable.runtime import ClockCallback, _same_callback

_logger = logging.getLogger(__name__)

# A deadline nearer than this waits for the next frame instead of a timer, so
# an animation ticks in step with the display.
_FRAME_WINDOW = 1.0 / 50.0


class _Entry:
    __slots__ = ("fn", "delay", "deadline", "armed", "is_interval")

    def __init__(self, fn: ClockCallback, delay: float, now: float, is_interval: bool) -> None:
        self.fn = fn
        self.delay = delay
        self.deadline = now + delay
        self.armed = now
        self.is_interval = is_interval


class BrowserClock:
    """A :class:`~nuiitivet.observable.runtime.Clock` on the browser's event loop.

    A browser gives the app no thread, so nothing here waits: the clock asks
    the page for a frame or a timer and fires what is due when :meth:`tick`
    runs. Callbacks fire on the one thread there is.
    """

    def __init__(
        self,
        request_frame: Callable[[], None],
        set_timeout: Callable[[float], Any],
        clear_timeout: Callable[[Any], None],
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        """
        Args:
            request_frame: Asks for :meth:`tick` to run on the next frame.
            set_timeout: Asks for :meth:`tick` to run after that many
                milliseconds, and returns a handle.
            clear_timeout: Cancels a handle ``set_timeout`` returned.
            now: The time source, in seconds.
        """
        self._request_frame = request_frame
        self._set_timeout = set_timeout
        self._clear_timeout = clear_timeout
        self._now = now
        self._entries: List[_Entry] = []
        self._timer: Optional[Any] = None

    def schedule_once(self, fn: ClockCallback, delay: float) -> None:
        self._arm(fn, float(delay), is_interval=False)

    def schedule_interval(self, fn: ClockCallback, interval: float) -> None:
        self._arm(fn, float(interval), is_interval=True)

    def unschedule(self, fn: ClockCallback) -> None:
        self._entries = [e for e in self._entries if not _same_callback(e.fn, fn)]

    def _arm(self, fn: ClockCallback, delay: float, *, is_interval: bool) -> None:
        self.unschedule(fn)
        self._entries.append(_Entry(fn, delay, self._now(), is_interval))
        self._wake()

    def tick(self) -> None:
        """Fire every callback that is due, then ask for the next wake-up."""
        now = self._now()
        for entry in [e for e in self._entries if e.deadline <= now]:
            # An earlier callback of this tick may have unscheduled it.
            if entry not in self._entries:
                continue
            elapsed = now - entry.armed
            if entry.is_interval:
                entry.armed = now
                entry.deadline += entry.delay
                # A callback slower than its period skips the ticks it missed.
                if entry.deadline <= now:
                    entry.deadline = now + entry.delay
            else:
                self._entries.remove(entry)
            try:
                entry.fn(elapsed)
            except Exception:
                exception_once(_logger, "browser_clock_callback_exc", "Scheduled callback failed")
        self._wake()

    def _wake(self) -> None:
        if self._timer is not None:
            self._clear_timeout(self._timer)
            self._timer = None
        if not self._entries:
            return
        wait = min(e.deadline for e in self._entries) - self._now()
        if wait <= _FRAME_WINDOW:
            self._request_frame()
        else:
            self._timer = self._set_timeout(wait * 1000.0)


__all__ = ["BrowserClock"]
