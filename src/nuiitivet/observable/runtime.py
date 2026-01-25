from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, Protocol

from nuiitivet.common.logging_once import exception_once


_logger = logging.getLogger(__name__)


class Clock(Protocol):
    """Clock API compatible with pyglet.clock."""

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:  # pragma: no cover - protocol
        raise NotImplementedError

    def unschedule(self, fn: Callable[[float], None]) -> None:  # pragma: no cover - protocol
        raise NotImplementedError


class _ThreadClock:
    """Fallback clock implementation using threading.Timer.

    This is used when no backend installs a UI clock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._timers: Dict[int, threading.Timer] = {}

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        def _run() -> None:
            try:
                fn(0.0)
            finally:
                with self._lock:
                    self._timers.pop(id(fn), None)

        timer = threading.Timer(float(delay), _run)
        timer.daemon = True
        with self._lock:
            old = self._timers.get(id(fn))
            if old is not None:
                try:
                    old.cancel()
                except Exception:
                    exception_once(_logger, "thread_clock_cancel_old_timer_exc", "Timer cancel failed")
            self._timers[id(fn)] = timer
        timer.start()

    def unschedule(self, fn: Callable[[float], None]) -> None:
        with self._lock:
            timer = self._timers.pop(id(fn), None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                exception_once(_logger, "thread_clock_cancel_timer_exc", "Timer cancel failed")


clock: Clock = _ThreadClock()


def set_clock(new_clock: Clock) -> None:
    global clock
    clock = new_clock
