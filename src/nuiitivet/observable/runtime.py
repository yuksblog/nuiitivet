from __future__ import annotations

import logging
import threading
from typing import Callable, List, Protocol, Tuple

from nuiitivet.common.logging_once import exception_once


_logger = logging.getLogger(__name__)


ClockCallback = Callable[[float], None]


class Clock(Protocol):
    """Clock API compatible with ``pyglet.clock``.

    Install an implementation with :func:`set_clock` to control when scheduled
    callbacks run — a test that drives ``dispatch_to_ui`` or a debounced
    observable needs this, since the default fallback clock fires on background
    threads at wall-clock time.

    Implementations must identify scheduled callbacks by **equality**, the rule
    ``pyglet.clock`` uses: ``unschedule(obj.method)`` has to cancel a timer
    armed with ``obj.method``, even though each attribute access produces a
    distinct bound-method object. Comparing by ``id()`` instead silently leaks
    timers.
    """

    def schedule_once(self, fn: ClockCallback, delay: float) -> None:  # pragma: no cover - protocol
        raise NotImplementedError

    def schedule_interval(self, fn: ClockCallback, interval: float) -> None:  # pragma: no cover - protocol
        raise NotImplementedError

    def unschedule(self, fn: ClockCallback) -> None:  # pragma: no cover - protocol
        raise NotImplementedError


def _same_callback(a: ClockCallback, b: ClockCallback) -> bool:
    """Compare scheduled callbacks the way ``pyglet.clock`` does.

    Equality, not identity: bound methods are equal but never identical, and
    callers routinely pass ``self._emit`` twice. Callables without ``__eq__``
    (``functools.partial``) fall back to Python's default identity comparison,
    which is the previous behaviour for them.
    """
    if a is b:
        return True
    try:
        return bool(a == b)
    except Exception:  # pragma: no cover - exotic __eq__
        exception_once(_logger, "thread_clock_callback_eq_exc", "Scheduled callback equality check raised")
        return False


class _ThreadClock:
    """Fallback clock implementation using threading.Timer.

    This is used when no backend installs a UI clock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Scanned lists rather than dicts: callbacks are matched by equality,
        # and an equality-based key would need a hashable callback.
        self._timers: List[Tuple[ClockCallback, threading.Timer]] = []
        self._intervals: List[Tuple[ClockCallback, threading.Thread]] = []

    def _pop_timers(self, fn: ClockCallback) -> List[threading.Timer]:
        """Remove and return every pending timer scheduled for ``fn``. Caller holds the lock."""
        matched: List[threading.Timer] = []
        remaining: List[Tuple[ClockCallback, threading.Timer]] = []
        for cb, timer in self._timers:
            if _same_callback(cb, fn):
                matched.append(timer)
            else:
                remaining.append((cb, timer))
        self._timers = remaining
        return matched

    def schedule_once(self, fn: ClockCallback, delay: float) -> None:
        timer = threading.Timer(float(delay), lambda: self._run_once(fn, timer))
        timer.daemon = True
        with self._lock:
            stale = self._pop_timers(fn)
            self._timers.append((fn, timer))
        for old in stale:
            self._cancel(old)
        timer.start()

    def _run_once(self, fn: ClockCallback, timer: threading.Timer) -> None:
        try:
            fn(0.0)
        finally:
            with self._lock:
                # Drop this timer only. A callback that reschedules itself has
                # already registered its replacement by the time we get here.
                self._timers = [entry for entry in self._timers if entry[1] is not timer]

    def schedule_interval(self, fn: ClockCallback, interval: float) -> None:
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
                        if not any(entry[1] is t for entry in self._intervals):
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
            self._intervals.append((fn, t))
        t.start()

    def unschedule(self, fn: ClockCallback) -> None:
        with self._lock:
            timers = self._pop_timers(fn)
            # Just drop the interval entries. The loop thread checks this list.
            # We don't have a direct handle to stop the thread other than
            # removing it from the list. (threading.Thread has no cancel())
            self._intervals = [entry for entry in self._intervals if not _same_callback(entry[0], fn)]

        for timer in timers:
            self._cancel(timer)

        # Interval thread will exit on next loop check.

    def _cancel(self, timer: threading.Timer) -> None:
        try:
            timer.cancel()
        except Exception:
            exception_once(_logger, "thread_clock_cancel_timer_exc", "Timer cancel failed")

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
            timers = [timer for _, timer in self._timers]
            self._timers.clear()
            self._intervals.clear()

        for timer in timers:
            self._cancel(timer)


clock: Clock = _ThreadClock()


def get_clock() -> Clock:
    """Return the clock currently installed.

    Read this instead of importing the ``clock`` module attribute:
    ``from ... import clock`` binds whatever was installed at *import* time,
    which is the fallback clock, since the backend installs its own during
    ``App.run()``. Save and restore around a test with this.
    """
    return clock


def set_clock(new_clock: Clock) -> None:
    """Install ``new_clock`` as the clock every deferred notification runs on."""
    global clock
    clock = new_clock
