"""A deterministic :class:`~nuiitivet.observable.runtime.Clock` for tests.

The fallback ``_ThreadClock`` fires scheduled callbacks on ``threading.Timer``
threads at wall-clock time, so a test that arms a debounce, a tooltip delay or
a ``dispatch_to_ui`` marshal races background threads. :class:`HarnessClock`
holds every scheduled callback in a queue and fires it only when the test
**pumps** — on the pumping thread, deterministically.

Real time, not virtual time: there is no ``advance()``. ``pump()`` fires what
is due *now*, so a delayed callback fires only after its delay has genuinely
elapsed. A synchronous test therefore never sees a delayed effect unless it
slept on purpose — the same thing a widget does on the first frame in
production.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from typing import List, Optional

from nuiitivet.observable.runtime import ClockCallback, _same_callback


_MAX_FIRES_PER_PUMP = 10_000


class NuiitivetClockWarning(Warning):
    """A test left scheduled clock callbacks due and unpumped at teardown."""


@dataclass(frozen=True)
class PendingCallback:
    """A snapshot of one callback scheduled on a :class:`HarnessClock`.

    ``delay`` is the one-shot delay or the interval period, as passed to the
    scheduling call. ``due`` reports whether the callback's deadline had passed
    when the snapshot was taken.
    """

    fn: ClockCallback
    delay: float
    is_interval: bool
    site: str
    due: bool


class _Entry:
    __slots__ = ("fn", "delay", "deadline", "is_interval", "site", "seq")

    def __init__(
        self,
        fn: ClockCallback,
        delay: float,
        deadline: float,
        is_interval: bool,
        site: str,
        seq: int,
    ) -> None:
        self.fn = fn
        self.delay = delay
        self.deadline = deadline
        self.is_interval = is_interval
        self.site = site
        self.seq = seq


def _caller_site() -> str:
    frame = sys._getframe(2)
    return f"{frame.f_code.co_filename}:{frame.f_lineno}"


class HarnessClock:
    """A :class:`~nuiitivet.observable.runtime.Clock` fired by pumping.

    Semantics follow ``pyglet.clock``, the production backend: callbacks are
    matched by **equality** (bound methods are equal but never identical), and
    scheduling the same callback twice arms it twice. ``schedule_interval``
    fires idealistically — an interval of 0.1 pumped after 1.0 s has elapsed
    fires ten times with ``dt == 0.1`` — with no drift compensation.

    Thread-safe: ``dispatch_to_ui`` schedules from worker threads. Callbacks
    fire outside the lock, on the pumping thread, and may schedule or
    unschedule freely while a pump is in progress; a callback that schedules
    another already-due callback has it fire in the same pump.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: List[_Entry] = []
        self._seq = 0

    # -- Clock protocol ----------------------------------------------------

    def schedule_once(self, fn: ClockCallback, delay: float) -> None:
        """Arm ``fn`` to fire once, ``delay`` seconds from now, when pumped."""
        now = time.monotonic()
        with self._lock:
            self._entries.append(
                _Entry(fn, float(delay), now + float(delay), False, _caller_site(), self._seq)
            )
            self._seq += 1

    def schedule_interval(self, fn: ClockCallback, interval: float) -> None:
        """Arm ``fn`` to fire every ``interval`` seconds, when pumped."""
        now = time.monotonic()
        with self._lock:
            self._entries.append(
                _Entry(fn, float(interval), now + float(interval), True, _caller_site(), self._seq)
            )
            self._seq += 1

    def unschedule(self, fn: ClockCallback) -> None:
        """Cancel every pending firing of ``fn``, matched by equality."""
        with self._lock:
            self._entries = [e for e in self._entries if not _same_callback(e.fn, fn)]

    # -- pumping -----------------------------------------------------------

    def pump(self) -> int:
        """Fire everything already due, in deadline order; return the count.

        Due entries scheduled *by* a fired callback fire in the same pump. An
        interval whose deadline lags fires once per elapsed period (``dt`` is
        the ideal period); an interval of zero or less fires once per pump.
        """
        return self._pump(immediate_only=False)

    def pump_immediate(self) -> int:
        """Fire only zero-delay one-shots; return the count.

        ``schedule_once(fn, 0)`` means "not on this call stack" — a marshal to
        the UI thread, or a deferral to the next frame. A synchronous test can
        honour that request (this call is the next stack), while no time has
        passed in it that the test chose — so delayed callbacks and intervals
        stay armed.
        """
        return self._pump(immediate_only=True)

    def _pump(self, *, immediate_only: bool) -> int:
        fired = 0
        # Intervals with a non-positive period are always due; fire them once
        # per pump instead of looping forever.
        seen_nonpositive: set[int] = set()
        while True:
            now = time.monotonic()
            with self._lock:
                entry = self._next_due(now, immediate_only, seen_nonpositive)
                if entry is None:
                    return fired
                if entry.is_interval:
                    if entry.delay <= 0.0:
                        seen_nonpositive.add(id(entry))
                        entry.deadline = now
                    # Ideal cadence: advance from the missed deadline, not from
                    # now, so a lagging interval catches up one period per fire.
                    entry.deadline += max(entry.delay, 0.0)
                else:
                    self._entries.remove(entry)
            if fired >= _MAX_FIRES_PER_PUMP:
                raise RuntimeError(
                    "HarnessClock.pump did not converge after "
                    f"{_MAX_FIRES_PER_PUMP} callbacks; last candidate was "
                    f"{entry.fn!r} scheduled at {entry.site}"
                )
            entry.fn(entry.delay)
            fired += 1

    def _next_due(
        self, now: float, immediate_only: bool, skip: set[int]
    ) -> Optional[_Entry]:
        """Earliest due entry, FIFO among equal deadlines. Caller holds the lock."""
        best: Optional[_Entry] = None
        for entry in self._entries:
            if immediate_only and (entry.is_interval or entry.delay != 0.0):
                continue
            if entry.deadline > now or id(entry) in skip:
                continue
            if best is None or (entry.deadline, entry.seq) < (best.deadline, best.seq):
                best = entry
        return best

    # -- queries -----------------------------------------------------------

    @property
    def due_now(self) -> bool:
        """Whether anything would fire if :meth:`pump` were called now."""
        now = time.monotonic()
        with self._lock:
            return any(e.deadline <= now for e in self._entries)

    @property
    def next_deadline(self) -> Optional[float]:
        """Seconds until the earliest callback is due — 0.0 when one already
        is — or ``None`` when nothing is armed."""
        now = time.monotonic()
        with self._lock:
            if not self._entries:
                return None
            return max(0.0, min(e.deadline for e in self._entries) - now)

    def pending(self) -> List[PendingCallback]:
        """Snapshot of everything still armed, in scheduling order."""
        now = time.monotonic()
        with self._lock:
            return [self._snapshot(e, now) for e in sorted(self._entries, key=lambda e: e.seq)]

    # -- teardown ----------------------------------------------------------

    def cancel_all(self) -> List[PendingCallback]:
        """Drop everything still armed and return it, in scheduling order.

        The return value is the teardown diagnostic: entries with ``due=True``
        were armed, elapsed, and never pumped.
        """
        now = time.monotonic()
        with self._lock:
            dropped = [self._snapshot(e, now) for e in sorted(self._entries, key=lambda e: e.seq)]
            self._entries.clear()
            return dropped

    @staticmethod
    def _snapshot(entry: _Entry, now: float) -> PendingCallback:
        return PendingCallback(
            fn=entry.fn,
            delay=entry.delay,
            is_interval=entry.is_interval,
            site=entry.site,
            due=entry.deadline <= now,
        )
