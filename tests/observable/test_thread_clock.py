"""Regression tests for the fallback ``_ThreadClock`` (#522).

These run against the **real** ``_ThreadClock``, on purpose. A fake clock that
fires callbacks on the thread that pumps it and unschedules by equality masks
every defect covered here.
"""

from __future__ import annotations

import threading
import time
from typing import Iterator, List, Tuple

import pytest

import nuiitivet.material as nv
from nuiitivet.observable import Clock, Observable
from nuiitivet.observable import runtime
from nuiitivet.observable.runtime import ClockCallback, _ThreadClock


# The debounce window and the settle time used to prove no *second* emission
# arrives. Generous enough not to flake on a loaded machine, short enough that
# the file stays fast.
_WINDOW = 0.05
_SETTLE = 0.3
_TIMEOUT = 2.0


class _CountingThreadClock:
    """Real ``_ThreadClock`` behaviour, plus a count of ``schedule_once`` calls.

    The busy-loop defect shows up as an unbounded call count, so counting is
    the assertion; delegation keeps the timing semantics honest.
    """

    def __init__(self) -> None:
        self._inner = _ThreadClock()
        self._lock = threading.Lock()
        self.schedule_once_calls = 0

    def schedule_once(self, fn: ClockCallback, delay: float) -> None:
        with self._lock:
            self.schedule_once_calls += 1
        self._inner.schedule_once(fn, delay)

    def schedule_interval(self, fn: ClockCallback, interval: float) -> None:
        self._inner.schedule_interval(fn, interval)

    def unschedule(self, fn: ClockCallback) -> None:
        self._inner.unschedule(fn)

    def cancel_all(self) -> None:
        self._inner.cancel_all()


@pytest.fixture
def thread_clock(monkeypatch) -> Iterator[_CountingThreadClock]:
    """Install a fresh thread-based clock and leave no timer behind."""
    clock = _CountingThreadClock()
    monkeypatch.setattr(runtime, "clock", clock)
    try:
        yield clock
    finally:
        clock.cancel_all()


class _Recorder:
    """Thread-safe subscriber sink."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: List[object] = []
        self.received = threading.Event()

    def __call__(self, value: object) -> None:
        with self._lock:
            self._values.append(value)
        self.received.set()

    @property
    def values(self) -> List[object]:
        with self._lock:
            return list(self._values)


class TestDebounceUnderThreadClock:
    def test_burst_emits_once(self, thread_clock: _CountingThreadClock) -> None:
        """A burst inside the window collapses to a single emission.

        Before the fix, ``unschedule(self._emit)`` missed — the bound method is
        a fresh object per access, and the clock keyed timers on ``id(fn)`` —
        so every write armed its own timer and the burst emitted N times.
        """
        source: Observable[str] = Observable("")
        debounced = source.debounce(_WINDOW)

        recorder = _Recorder()
        debounced.subscribe(recorder)

        for value in ("a", "b", "c", "d", "e"):
            source.value = value

        assert recorder.received.wait(_TIMEOUT), "debounce never emitted"
        time.sleep(_SETTLE)

        assert recorder.values == ["e"]

    def test_unschedule_cancels_pending_emit(self, thread_clock: _CountingThreadClock) -> None:
        """A write followed by disposal of the window leaves nothing armed."""
        source: Observable[str] = Observable("")
        debounced = source.debounce(_WINDOW)

        recorder = _Recorder()
        debounced.subscribe(recorder)

        source.value = "a"
        runtime.clock.unschedule(debounced._emit)

        time.sleep(_WINDOW + _SETTLE)
        assert recorder.values == []


class TestThreadClockCallbackIdentity:
    def test_unschedule_matches_equal_bound_method(self, thread_clock: _CountingThreadClock) -> None:
        """``unschedule`` cancels a timer armed with an equal-but-not-identical callable."""

        class Target:
            def __init__(self) -> None:
                self.fired = threading.Event()

            def tick(self, dt: float) -> None:
                self.fired.set()

        target = Target()
        assert target.tick is not target.tick, "bound methods are expected to be non-identical"
        assert target.tick == target.tick

        runtime.clock.schedule_once(target.tick, _WINDOW)
        runtime.clock.unschedule(target.tick)

        assert not target.fired.wait(_WINDOW + _SETTLE)

    def test_reschedule_replaces_previous_timer(self, thread_clock: _CountingThreadClock) -> None:
        """Arming an equal callable again cancels the previous timer instead of stacking."""

        class Target:
            def __init__(self) -> None:
                self.calls = 0

            def tick(self, dt: float) -> None:
                self.calls += 1

        target = Target()
        for _ in range(5):
            runtime.clock.schedule_once(target.tick, _WINDOW)

        time.sleep(_WINDOW + _SETTLE)
        assert target.calls == 1

    def test_partial_falls_back_to_identity(self, thread_clock: _CountingThreadClock) -> None:
        """Callables without ``__eq__`` keep the previous identity-based behaviour."""
        import functools

        fired: List[str] = []

        def record(dt: float, tag: str) -> None:
            fired.append(tag)

        first = functools.partial(record, tag="first")
        second = functools.partial(record, tag="second")

        runtime.clock.schedule_once(first, _WINDOW)
        runtime.clock.schedule_once(second, _WINDOW)
        runtime.clock.unschedule(first)

        time.sleep(_WINDOW + _SETTLE)
        assert fired == ["second"]


class TestCrossThreadWritesUnderThreadClock:
    def test_single_worker_write_delivers_once(self, thread_clock: _CountingThreadClock) -> None:
        """A worker-thread write reaches subscribers exactly once.

        Before the fix the deferred flush re-entered the setter, which was
        still off the main thread, so it queued the value again and rescheduled
        forever: thousands of ``schedule_once`` calls and zero deliveries.
        """
        obs: Observable[int] = Observable(0)

        recorder = _Recorder()
        obs.subscribe(recorder)

        def worker() -> None:
            obs.value = 42

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        assert recorder.received.wait(_TIMEOUT), "the marshalled write never delivered"
        time.sleep(_SETTLE)

        assert recorder.values == [42]
        assert obs.value == 42
        assert thread_clock.schedule_once_calls == 1

    def test_burst_of_worker_writes_settles(self, thread_clock: _CountingThreadClock) -> None:
        """Rapid worker writes coalesce, land on the final value, and stay bounded."""
        writes = 7
        obs: Observable[int] = Observable(0)

        recorder = _Recorder()
        obs.subscribe(recorder)

        def worker() -> None:
            for i in range(1, writes + 1):
                obs.value = i

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        deadline = time.monotonic() + _TIMEOUT
        while time.monotonic() < deadline and obs.value != writes:
            time.sleep(0.01)
        time.sleep(_SETTLE)

        assert obs.value == writes
        assert recorder.values, "the marshalled write never delivered"
        assert recorder.values[-1] == writes
        # Coalescing means at most one scheduled flush per write, never more.
        assert 1 <= thread_clock.schedule_once_calls <= writes

    def test_main_thread_write_is_immediate(self, thread_clock: _CountingThreadClock) -> None:
        """A write already on the UI thread still applies synchronously."""
        obs: Observable[int] = Observable(0)

        recorder = _Recorder()
        obs.subscribe(recorder)

        obs.value = 5

        assert obs.value == 5
        assert recorder.values == [5]
        assert thread_clock.schedule_once_calls == 0


def test_interval_stops_after_unschedule(thread_clock: _CountingThreadClock) -> None:
    """``schedule_interval`` / ``unschedule`` also match by equality."""

    class Ticker:
        def __init__(self) -> None:
            self.calls = 0

        def tick(self, dt: float) -> None:
            self.calls += 1

    ticker = Ticker()
    runtime.clock.schedule_interval(ticker.tick, 0.01)

    deadline = time.monotonic() + _TIMEOUT
    while time.monotonic() < deadline and ticker.calls == 0:
        time.sleep(0.01)
    assert ticker.calls > 0, "interval never fired"

    runtime.clock.unschedule(ticker.tick)
    time.sleep(_SETTLE)
    settled = ticker.calls
    time.sleep(_SETTLE)

    assert ticker.calls == settled


def test_manual_clock_drives_a_marshalled_write(monkeypatch) -> None:
    """A hand-rolled ``Clock`` — the shape the guide recommends — works end to end.

    This is the documented way to test a cross-thread write deterministically:
    install a clock that queues callbacks and run them on demand.
    """

    class ManualClock:
        def __init__(self) -> None:
            self._pending: List[Tuple[float, ClockCallback]] = []

        def schedule_once(self, fn: ClockCallback, delay: float) -> None:
            self.unschedule(fn)
            self._pending.append((delay, fn))

        def schedule_interval(self, fn: ClockCallback, interval: float) -> None:
            self._pending.append((interval, fn))

        def unschedule(self, fn: ClockCallback) -> None:
            self._pending = [entry for entry in self._pending if entry[1] != fn]

        def tick(self, dt: float = 0.0) -> None:
            pending, self._pending = self._pending, []
            for _, fn in pending:
                fn(dt)

    clock: Clock = ManualClock()
    monkeypatch.setattr(runtime, "clock", clock)
    assert nv.Clocks.get() is clock, "Clocks.get must report the installed clock, not an import-time snapshot"

    obs: Observable[int] = Observable(0)

    recorder = _Recorder()
    obs.subscribe(recorder)

    thread = threading.Thread(target=lambda: setattr(obs, "value", 9))
    thread.start()
    thread.join()

    assert recorder.values == []
    assert obs.value == 0

    clock.tick()  # type: ignore[attr-defined]

    assert recorder.values == [9]
    assert obs.value == 9


def test_opting_out_delivers_every_intermediate_value(thread_clock: _CountingThreadClock) -> None:
    """``dispatch=False`` is the escape hatch from marshalling *and* coalescing.

    Marshalling keeps only the latest value per tick, which is what a UI wants
    and what a logic-layer consumer counting every step does not. Opting out
    buys back the full sequence, delivered inline on the writing thread.
    """
    obs: Observable[int] = Observable(0, dispatch=False)

    recorder = _Recorder()
    obs.subscribe(recorder)

    def worker() -> None:
        for i in range(1, 6):
            obs.value = i

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    # No clock involved at all: the writes applied where they were made.
    assert thread_clock.schedule_once_calls == 0
    assert obs.value == 5
    assert recorder.values == [1, 2, 3, 4, 5]


def test_one_servicing_thread_regardless_of_how_many_callbacks() -> None:
    """The fallback clock costs one thread, not one per armed callback.

    The previous implementation spent a ``threading.Timer`` -- a thread -- per
    ``schedule_once``, which every cross-thread observable write now reaches.
    """
    def make_noop() -> ClockCallback:
        def noop(dt: float) -> None:
            return None

        return noop

    clock = _ThreadClock()
    before = threading.active_count()
    try:
        # Distinct callables: arming re-arms by equality, so one shared
        # function would leave a single entry rather than fifty.
        for _ in range(50):
            clock.schedule_once(make_noop(), _WINDOW * 4)
        clock.schedule_interval(make_noop(), _WINDOW * 4)

        assert clock.pending_count() == 51
        # One servicing thread, started lazily on the first arm.
        assert threading.active_count() - before == 1
    finally:
        clock.cancel_all()


class _RecordingClock:
    """Records what is armed on it. Fires nothing on its own."""

    def __init__(self) -> None:
        self.intervals: List[Tuple[ClockCallback, float]] = []
        self.onces: List[Tuple[ClockCallback, float]] = []

    def schedule_once(self, fn: ClockCallback, delay: float) -> None:
        self.onces.append((fn, delay))

    def schedule_interval(self, fn: ClockCallback, interval: float) -> None:
        self.intervals.append((fn, interval))

    def unschedule(self, fn: ClockCallback) -> None:
        self.intervals = [e for e in self.intervals if e[0] != fn]
        self.onces = [e for e in self.onces if e[0] != fn]


class TestHandoverToTheInstalledClock:
    """#655: callbacks armed before a UI clock existed must not stay on the thread.

    A widget mounted while ``App()`` is being constructed arms on the fallback
    clock, and ``set_clock`` used to only rebind the module global -- leaving the
    callback firing on the servicing thread for the life of the process.
    """

    @pytest.fixture
    def fallback(self, monkeypatch) -> Iterator[_ThreadClock]:
        clock = _ThreadClock()
        monkeypatch.setattr(runtime, "clock", clock)
        try:
            yield clock
        finally:
            clock.cancel_all()

    def test_interval_moves_to_the_new_clock(self, fallback: _ThreadClock) -> None:
        def tick(dt: float) -> None:
            return None

        fallback.schedule_interval(tick, _WINDOW)
        installed = _RecordingClock()

        runtime.set_clock(installed)

        assert installed.intervals == [(tick, _WINDOW)]
        assert fallback.pending_count() == 0

    def test_one_shot_keeps_its_remaining_time(self, fallback: _ThreadClock) -> None:
        def fire(dt: float) -> None:
            return None

        fallback.schedule_once(fire, _TIMEOUT)
        installed = _RecordingClock()

        runtime.set_clock(installed)

        assert len(installed.onces) == 1
        moved_fn, remaining = installed.onces[0]
        assert moved_fn == fire
        # The deadline travels with the entry rather than restarting.
        assert 0.0 < remaining <= _TIMEOUT
        assert installed.intervals == []

    def test_moved_callback_stops_firing_on_the_servicing_thread(self, fallback: _ThreadClock) -> None:
        fired = threading.Event()

        def tick(dt: float) -> None:
            fired.set()

        fallback.schedule_interval(tick, _WINDOW)
        runtime.set_clock(_RecordingClock())

        # The recording clock never fires, so anything arriving here came from
        # the fallback's worker -- exactly what #655 was.
        assert not fired.wait(_SETTLE)

    def test_installing_the_same_clock_twice_does_not_re_arm(self, fallback: _ThreadClock) -> None:
        def tick(dt: float) -> None:
            return None

        fallback.schedule_interval(tick, _WINDOW)
        installed = _RecordingClock()

        runtime.set_clock(installed)
        runtime.set_clock(installed)

        assert installed.intervals == [(tick, _WINDOW)]

    def test_handover_from_a_non_fallback_clock_is_skipped(self, monkeypatch) -> None:
        """Only the fallback can enumerate a schedule -- and only it needs to."""
        previous = _RecordingClock()

        def tick(dt: float) -> None:
            return None

        previous.schedule_interval(tick, _WINDOW)
        monkeypatch.setattr(runtime, "clock", previous)
        installed = _RecordingClock()

        runtime.set_clock(installed)

        assert installed.intervals == []
        assert previous.intervals == [(tick, _WINDOW)]
