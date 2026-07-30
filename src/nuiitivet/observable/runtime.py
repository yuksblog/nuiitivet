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

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:  # pragma: no cover - protocol
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
        self._intervals: Dict[int, threading.Thread] = {}

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

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        # Avoid creating recursive threads. Use a persistent loop for interval tasks.
        # But for simplicity in this fallback clock, we just launch ONE daemon thread per interval task
        # that sleeps and calls the function repeatedly.

        def _loop() -> None:
            import time

            while True:
                start_time = time.perf_counter()
                try:
                    # Check if still scheduled
                    with self._lock:
                        if id(fn) not in self._intervals:
                            break
                    fn(interval)
                except Exception:
                    exception_once(_logger, "thread_clock_interval_exc", "Interval callback failed")

                # Sleep for the remainder
                elapsed = time.perf_counter() - start_time
                wait_time = max(0.0, interval - elapsed)
                if wait_time > 0:
                    time.sleep(wait_time)
                else:
                    # If lagging, invoke immediately but yield time slice
                    time.sleep(0.001)

        t = threading.Thread(target=_loop, daemon=True)
        with self._lock:
            self._intervals[id(fn)] = t
        t.start()

    def _schedule_interval_internal(self, fn: Callable[[float], None], interval: float) -> None:
        # Removed recursive logic.
        pass

    def unschedule(self, fn: Callable[[float], None]) -> None:
        with self._lock:
            timer = self._timers.pop(id(fn), None)
            # Just pop from _intervals. The loop thread checks this dict.
            # We don't have a direct handle to stop the thread other than removing from dict.
            # (Threading.Thread doesn't have cancel())
            self._intervals.pop(id(fn), None)

        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                exception_once(_logger, "thread_clock_cancel_timer_exc", "Timer cancel failed")

        # Interval thread will exit on next loop check.

    def cancel_all(self) -> None:
        """Cancel every pending timer and stop every interval loop.

        Callbacks scheduled on this fallback clock run on background threads,
        so anything still pending fires later at an arbitrary moment — long
        after whoever scheduled it is gone. Callbacks that touch the widget
        tree then trip :func:`assert_ui_thread` off the UI thread, and the
        resulting error surfaces in unrelated code. This drops the whole
        schedule in one call, for teardown paths that must leave no timer
        behind. Interval loops exit on their next scheduling check.
        """
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
            self._intervals.clear()

        for timer in timers:
            try:
                timer.cancel()
            except Exception:
                exception_once(_logger, "thread_clock_cancel_timer_exc", "Timer cancel failed")


clock: Clock = _ThreadClock()


def set_clock(new_clock: Clock) -> None:
    global clock
    clock = new_clock
