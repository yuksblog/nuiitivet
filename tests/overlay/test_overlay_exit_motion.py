"""Regression: overlay exit must run on the spec's exit motion.

The exit definition is stored under ``exit_``, and the overlay's motion lookup
used to read ``getattr(spec, "exit")`` — missing it and silently replacing
every overlay exit (dialog close, sheet dismissal, snackbar dismissal) with the
0.6 s engine default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nuiitivet.layout.stack import Stack
from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.material.transition_spec import MaterialTransitions
from nuiitivet.observable import runtime as observable_runtime
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.overlay_route import OverlayRoute


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


@dataclass
class _Env:
    clock: _FakeClock
    overlay: Overlay


def _shown_dialog_env() -> _Env:
    clock = observable_runtime.clock
    assert isinstance(clock, _FakeClock)
    overlay = Overlay()
    root = Stack(children=[overlay], alignment="center")
    root.mount(_DummyApp())
    root.layout(800, 600)

    route = OverlayRoute(
        builder=lambda: BasicDialog(title="Exit motion"),
        transition_spec=MaterialTransitions.dialog(),
    )
    overlay.show(route, backdrop=True)
    return _Env(clock=clock, overlay=overlay)


def test_dialog_exit_finishes_on_spec_motion_duration() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        env = _shown_dialog_env()

        # Finish the enter transition (default spatial, 0.5 s).
        for _ in range(14):
            env.clock.advance(0.05)
        assert env.overlay.has_entries() is True

        entry = next(iter(env.overlay._entry_to_route.keys()))
        env.overlay.remove_entry(entry)

        # The dialog exit motion is 0.15 s. Under the regression the engine fell
        # back to its 0.6 s default, so the entry would still be present here.
        for _ in range(6):
            env.clock.advance(0.05)
        assert env.overlay.has_entries() is False
    finally:
        observable_runtime.set_clock(prev_clock)
