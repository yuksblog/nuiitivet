from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nuiitivet.layout.stack import Stack
from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.observable import runtime as observable_runtime
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.overlay_entry import OverlayEntry
from nuiitivet.overlay.overlay import _OverlayLayer
from nuiitivet.transition.spec import TransitionPhase


class _FakeClock:
    def __init__(self) -> None:
        self._interval_callbacks: list[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        del fn, delay

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        del interval
        if fn not in self._interval_callbacks:
            self._interval_callbacks.append(fn)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self._interval_callbacks = [callback for callback in self._interval_callbacks if callback is not fn]

    def advance(self, dt: float) -> None:
        for callback in list(self._interval_callbacks):
            callback(dt)


class _DummyApp:
    def invalidate(self, immediate: bool = False) -> None:
        del immediate


@dataclass(frozen=True, slots=True)
class _AnimatedTransitionSpec:
    pass


def test_overlay_layer_enter_exit_lifecycle_is_transition_driven() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        overlay = Overlay()
        root = Stack(children=[overlay], alignment="center")
        root.mount(_DummyApp())
        root.layout(800, 600)

        overlay.show(BasicDialog(title="Lifecycle"), backdrop=True, transition_spec=_AnimatedTransitionSpec())

        entry = next(iter(overlay._entry_to_layer.keys()))
        layer = overlay._entry_to_layer[entry]
        assert isinstance(layer, _OverlayLayer)
        assert layer.transition_phase_obs.value is TransitionPhase.ENTER
        assert layer.transition_state.phase_obs is layer.transition_phase_obs
        assert layer.transition_state.progress_obs is layer.transition_progress_obs

        fake_clock.advance(0.7)
        assert layer.transition_phase_obs.value is TransitionPhase.ACTIVE
        assert abs(float(layer.transition_progress_obs.value) - 1.0) < 1e-6

        overlay.remove_entry(entry)
        assert any(r is layer for r in overlay._layer_stack.layers)
        assert layer.transition_phase_obs.value is TransitionPhase.EXIT

        fake_clock.advance(0.7)
        assert not any(r is layer for r in overlay._layer_stack.layers)
        assert overlay.has_entries() is False
    finally:
        observable_runtime.set_clock(prev_clock)


def test_overlay_transition_does_not_leak_clock_callbacks_after_repeated_show_close() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        overlay = Overlay()
        root = Stack(children=[overlay], alignment="center")
        root.mount(_DummyApp())
        root.layout(800, 600)

        for _ in range(10):
            overlay.show(BasicDialog(title="Perf"), backdrop=True, transition_spec=_AnimatedTransitionSpec())
            fake_clock.advance(0.7)  # finish enter
            entry = next(iter(overlay._entry_to_layer.keys()))
            overlay.remove_entry(entry)
            fake_clock.advance(0.7)  # finish exit

        assert overlay.has_entries() is False
        assert len(fake_clock._interval_callbacks) == 0
    finally:
        observable_runtime.set_clock(prev_clock)


def test_overlay_on_disposed_runs_once_after_exit_complete() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        overlay = Overlay()
        root = Stack(children=[overlay], alignment="center")
        root.mount(_DummyApp())
        root.layout(800, 600)

        callback_calls: list[bool] = []

        def _build() -> BasicDialog:
            return BasicDialog(title="Dispose ordering")

        def _on_disposed() -> None:
            callback_calls.append(bool(overlay._layer_stack.layers))

        entry = OverlayEntry(builder=_build, on_dispose=_on_disposed)
        overlay._insert_entry_layer(entry, _OverlayLayer(entry, transition_spec=_AnimatedTransitionSpec()))

        fake_clock.advance(0.7)  # finish enter
        overlay.remove_entry(entry)

        assert callback_calls == []

        fake_clock.advance(0.7)  # finish exit

        assert callback_calls == [False]
        overlay.remove_entry(entry)
        assert callback_calls == [False]
    finally:
        observable_runtime.set_clock(prev_clock)
