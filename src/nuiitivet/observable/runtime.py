from __future__ import annotations

import logging
import threading
import time
from typing import Callable, List, Optional, Protocol

from nuiitivet.common.logging_once import exception_once


_logger = logging.getLogger(__name__)


ClockCallback = Callable[[float], None]


class Clock(Protocol):
    """Clock API compatible with ``pyglet.clock``.

    Install an implementation with :func:`set_clock` to control when scheduled
    callbacks run — a test that drives a cross-thread observable write or a
    debounced observable needs this, since the default fallback clock fires on
    a background thread at wall-clock time.

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


class _Entry:
    """One armed callback on the fallback clock."""

    __slots__ = ("fn", "delay", "deadline", "is_interval")

    def __init__(self, fn: ClockCallback, delay: float, deadline: float, is_interval: bool) -> None:
        self.fn = fn
        self.delay = delay
        self.deadline = deadline
        self.is_interval = is_interval


class _ThreadClock:
    """Fallback clock used when no backend has installed a UI clock.

    **One** daemon thread services every armed callback, waking on a condition
    variable when the earliest deadline arrives or when a nearer one is armed.
    The earlier implementation spent a ``threading.Timer`` -- a thread -- per
    ``schedule_once`` and another per interval, which an ``Observable`` write
    from a worker reaches on every tick now that dispatch is the default.

    Callbacks still fire on that servicing thread, not on any UI thread: with
    no backend running there is no UI thread to marshal to. Tests get
    determinism from :class:`~nuiitivet.testing.clock.HarnessClock` instead.

    Entries live in a scanned list rather than a heap: callbacks are matched by
    **equality** (see :func:`_same_callback`), so an entry can be cancelled by a
    value that is merely equal to the one that armed it, and lazy deletion off a
    heap would have to scan anyway. The list stays short -- one entry per armed
    callback -- and this mirrors ``HarnessClock``, which scans for the same
    reason.
    """

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._entries: List[_Entry] = []
        self._worker: Optional[threading.Thread] = None

    # -- Clock protocol ----------------------------------------------------

    def schedule_once(self, fn: ClockCallback, delay: float) -> None:
        self._arm(fn, float(delay), is_interval=False)

    def schedule_interval(self, fn: ClockCallback, interval: float) -> None:
        self._arm(fn, float(interval), is_interval=True)

    def unschedule(self, fn: ClockCallback) -> None:
        with self._cond:
            self._entries = [e for e in self._entries if not _same_callback(e.fn, fn)]
            self._cond.notify()

    def _arm(self, fn: ClockCallback, delay: float, *, is_interval: bool) -> None:
        """Replace anything armed for ``fn`` with a fresh entry, and wake the worker.

        Replacing rather than appending is what the previous implementation did
        for one-shots, and what callers depend on: ``DebouncedObservable``
        re-arms on every keystroke and expects one pending emit, not five.
        """
        with self._cond:
            self._entries = [e for e in self._entries if not _same_callback(e.fn, fn)]
            self._entries.append(_Entry(fn, delay, time.monotonic() + delay, is_interval))
            self._ensure_worker()
            self._cond.notify()

    # -- servicing ---------------------------------------------------------

    def _ensure_worker(self) -> None:
        """Start the servicing thread on first use. Caller holds the condition."""
        if self._worker is not None:
            return
        self._worker = threading.Thread(target=self._run, name="nuiitivet-clock", daemon=True)
        self._worker.start()

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._entries:
                    self._cond.wait()
                now = time.monotonic()
                entry = min(self._entries, key=lambda e: e.deadline)
                if entry.deadline > now:
                    self._cond.wait(entry.deadline - now)
                    # Re-scan rather than fire: the wait may have ended because
                    # something nearer was armed, or this entry unscheduled.
                    continue
                if entry.is_interval:
                    # Advance from the deadline so cadence does not drift, but
                    # never into a backlog: a callback slower than its period
                    # skips the missed ticks instead of firing a catch-up burst.
                    entry.deadline = max(now, entry.deadline + entry.delay)
                else:
                    self._entries.remove(entry)
            try:
                entry.fn(entry.delay)
            except Exception:
                exception_once(_logger, "thread_clock_callback_exc", "Scheduled callback failed")

    # -- teardown ----------------------------------------------------------

    def cancel_all(self) -> None:
        """Drop every armed callback, one-shot and interval alike.

        Callbacks scheduled on this fallback clock run on the servicing thread,
        so anything still pending fires later at an arbitrary moment — long
        after whoever scheduled it is gone. Callbacks that touch the widget
        tree then trip :func:`assert_ui_thread` off the UI thread, and the
        resulting error surfaces in unrelated code. This drops the whole
        schedule in one call, for teardown paths that must leave no timer
        behind.
        """
        with self._cond:
            self._entries.clear()
            self._cond.notify()

    def pending_count(self) -> int:
        """How many callbacks are armed. For tests and teardown diagnostics."""
        with self._cond:
            return len(self._entries)


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
