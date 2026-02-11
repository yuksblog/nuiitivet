from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nuiitivet.animation import Animation, AnimationManager
from nuiitivet.observable import runtime as observable_runtime


class _DummyApp:
    def __init__(self) -> None:
        self.invalidate_calls = 0
        self.immediate_calls = 0

    def invalidate(self, immediate: bool = False) -> None:
        self.invalidate_calls += 1
        if immediate:
            self.immediate_calls += 1


@dataclass
class _ScheduledCall:
    when_s: float
    fn: Callable[[float], None]


class _FakeClock:
    def __init__(self) -> None:
        self._now = 0.0
        self._scheduled: list[_ScheduledCall] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        self.unschedule(fn)
        self._scheduled.append(_ScheduledCall(self._now + float(delay), fn))
        self._scheduled.sort(key=lambda c: c.when_s)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self._scheduled = [c for c in self._scheduled if c.fn is not fn]

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        pass

    def advance(self, dt: float) -> None:
        self._now += float(dt)
        ready = [c for c in self._scheduled if c.when_s <= self._now]
        self._scheduled = [c for c in self._scheduled if c.when_s > self._now]
        for c in ready:
            c.fn(0.0)


def test_animation_manager_does_not_invalidate_during_delay() -> None:
    app = _DummyApp()
    mgr = AnimationManager(app)

    anim = Animation(duration=0.1, delay=1.0, on_update=lambda _p: None)
    mgr.start(anim)

    # start() triggers a single invalidate
    assert app.invalidate_calls == 1

    # While we're still in the delay period, no additional invalidations should occur.
    for _ in range(5):
        mgr.step(0.1)

    assert anim.is_alive
    assert app.invalidate_calls == 1


def test_animation_manager_wakes_up_at_delay_end_via_clock() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        app = _DummyApp()
        mgr = AnimationManager(app)

        anim = Animation(duration=0.1, delay=0.5, on_update=lambda _p: None)
        mgr.start(anim)
        assert app.invalidate_calls == 1

        # No frames stepped: the manager must request a draw when delay elapses.
        fake_clock.advance(0.5)
        assert app.invalidate_calls == 2
        assert app.immediate_calls == 1
    finally:
        observable_runtime.set_clock(prev_clock)
