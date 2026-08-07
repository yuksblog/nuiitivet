"""``set()`` is the expression-position spelling of the ``.value`` setter (#500).

A Python lambda cannot assign, so callback props and ``subscribe`` lambdas used
to reach for ``setattr(obs, "value", v)``. ``set()`` replaces that, and must be
the *same* write - these tests pin it to the setter's behaviour rather than to a
second code path.
"""

from __future__ import annotations

import threading
from typing import Callable

from nuiitivet.observable import Observable, batch
from nuiitivet.observable import runtime
from nuiitivet.observable.computed import ComputedObservable
from nuiitivet.observable.value import _ObservableValue


def test_set_writes_and_notifies():
    obs = Observable(0)
    seen: list[int] = []
    obs.subscribe(seen.append)

    obs.set(3)

    assert obs.value == 3
    assert seen == [3]


def test_set_de_dupes_like_the_setter():
    obs = Observable("ready")
    seen: list[str] = []
    obs.subscribe(seen.append)

    obs.set("ready")
    assert seen == []

    obs.set("go")
    assert seen == ["go"]


def test_set_honours_custom_compare():
    # compare says "never equal", so even an identical write must notify.
    obs = Observable(0, compare=lambda a, b: False)
    seen: list[int] = []
    obs.subscribe(seen.append)

    obs.set(0)
    assert seen == [0]


def test_set_works_through_the_descriptor():
    class State:
        count = Observable(0)

    state = State()
    seen: list[int] = []
    state.count.subscribe(seen.append)

    state.count.set(5)

    # Reading through the descriptor sees the same storage the write landed in.
    assert state.count.value == 5
    assert seen == [5]


def test_set_is_usable_from_a_lambda():
    """The motivating case: a write where only an expression is allowed."""
    expanded = Observable(False)
    on_click = lambda: expanded.set(not expanded.value)  # noqa: E731

    on_click()
    assert expanded.value is True

    on_click()
    assert expanded.value is False


def test_set_participates_in_batching():
    price = Observable(100)
    quantity = Observable(2)
    total = ComputedObservable(lambda: price.value * quantity.value)

    recomputed: list[int] = []
    total.subscribe(recomputed.append)

    with batch():
        price.set(200)
        quantity.set(3)

    # One recomputation for the pair, not one per write.
    assert recomputed == [600]


def test_set_defers_to_the_ui_thread_like_the_setter():
    # A recording clock keeps the deferral observable; the default fallback
    # clock would fire the callback on its own timer thread.
    prev_clock = runtime.clock
    scheduled: list[Callable[[float], None]] = []

    class _RecordingClock:
        def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
            scheduled.append(fn)

        def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
            raise AssertionError("unexpected schedule_interval")

        def unschedule(self, fn: Callable[[float], None]) -> None:
            pass

    runtime.set_clock(_RecordingClock())
    try:
        obs = _ObservableValue(0).dispatch_to_ui()
        seen: list[int] = []
        obs.subscribe(seen.append)

        worker = threading.Thread(target=lambda: obs.set(7))
        worker.start()
        worker.join()

        # Off-thread writes are queued for the clock, not applied inline.
        assert obs.value == 0
        assert seen == []
        assert len(scheduled) == 1

        # Draining on the main thread applies it, exactly as for ``.value =``.
        scheduled[0](0.0)
        assert obs.value == 7
        assert seen == [7]
    finally:
        runtime.set_clock(prev_clock)


def test_read_only_observables_have_no_set():
    computed = ComputedObservable(lambda: 1)
    assert not hasattr(computed, "set")
