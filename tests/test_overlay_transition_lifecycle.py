from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nuiitivet.layout.stack import Stack
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.observable import runtime as observable_runtime
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.dialog_route import DialogRoute
from nuiitivet.overlay.overlay_entry import OverlayEntry
from nuiitivet.overlay.overlay import _OverlayEntryRoute
from nuiitivet.navigation.transition_spec import TransitionPhase


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


def test_overlay_route_enter_exit_lifecycle_is_transition_driven() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        overlay = Overlay()
        root = Stack(children=[overlay], alignment="center")
        root.mount(_DummyApp())
        root.layout(800, 600)

        route = DialogRoute(
            builder=lambda: AlertDialog(title="Lifecycle"),
            transition_spec=_AnimatedTransitionSpec(),
            barrier_dismissible=False,
        )
        overlay.show(route)

        entry = next(iter(overlay._entry_to_route.keys()))
        modal_route = overlay._entry_to_route[entry]
        assert isinstance(modal_route, _OverlayEntryRoute)
        assert modal_route.transition_phase_obs.value is TransitionPhase.ENTER
        assert modal_route.transition_state.phase_obs is modal_route.transition_phase_obs
        assert modal_route.transition_state.progress_obs is modal_route.transition_progress_obs
        assert not hasattr(modal_route, "_overlay_route_frame_obs")
        assert not hasattr(modal_route, "_overlay_content_opacity_obs")
        assert not hasattr(modal_route, "_overlay_content_scale_obs")
        assert not hasattr(modal_route, "_overlay_barrier_opacity_obs")

        fake_clock.advance(0.7)
        assert modal_route.transition_phase_obs.value is TransitionPhase.ACTIVE
        assert abs(float(modal_route.transition_progress_obs.value) - 1.0) < 1e-6

        overlay.remove_entry(entry)
        routes_during_exit = overlay._modal_navigator._routes  # type: ignore[attr-defined]
        assert any(r is modal_route for r in routes_during_exit)
        assert modal_route.transition_phase_obs.value is TransitionPhase.EXIT

        fake_clock.advance(0.7)
        routes_after_exit = overlay._modal_navigator._routes  # type: ignore[attr-defined]
        assert not any(r is modal_route for r in routes_after_exit)
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
            route = DialogRoute(
                builder=lambda: AlertDialog(title="Perf"),
                transition_spec=_AnimatedTransitionSpec(),
                barrier_dismissible=False,
            )
            overlay.show(route)
            fake_clock.advance(0.7)  # finish enter
            entry = next(iter(overlay._entry_to_route.keys()))
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

        def _build() -> AlertDialog:
            return AlertDialog(title="Dispose ordering")

        def _on_disposed() -> None:
            routes = overlay._modal_navigator._routes  # type: ignore[attr-defined]
            has_modal = any(isinstance(route, _OverlayEntryRoute) for route in routes)
            callback_calls.append(has_modal)

        entry = OverlayEntry(builder=_build, on_dispose=_on_disposed)
        route = DialogRoute(
            builder=entry.build_widget,
            transition_spec=_AnimatedTransitionSpec(),
            barrier_dismissible=False,
        )
        overlay._insert_entry_with_route(entry, route)

        fake_clock.advance(0.7)  # finish enter
        overlay.remove_entry(entry)

        assert callback_calls == []

        fake_clock.advance(0.7)  # finish exit

        assert callback_calls == [False]
        overlay.remove_entry(entry)
        assert callback_calls == [False]
    finally:
        observable_runtime.set_clock(prev_clock)
