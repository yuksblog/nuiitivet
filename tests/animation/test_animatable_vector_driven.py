from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nuiitivet.animation import Animatable, LinearMotion, SpringMotion, VectorConverter
from nuiitivet.observable import runtime as observable_runtime


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float


class Vec2Converter(VectorConverter[Vec2]):
    def to_vector(self, value: Vec2) -> list[float]:
        return [value.x, value.y]

    def from_vector(self, vector: list[float]) -> Vec2:
        return Vec2(vector[0], vector[1])


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


def test_animatable_float_uses_default_converter_with_motion() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        anim = Animatable(0.0, motion=LinearMotion(1.0))
        anim.target = 10.0

        fake_clock.advance(0.5)
        assert anim.value == 5.0

        fake_clock.advance(0.5)
        assert anim.value == 10.0
    finally:
        observable_runtime.set_clock(prev_clock)


def test_animatable_supports_custom_vector_converter() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        anim = Animatable.vector(Vec2(0.0, 10.0), Vec2Converter(), motion=LinearMotion(1.0))
        anim.target = Vec2(10.0, 20.0)

        fake_clock.advance(0.5)
        assert anim.value == Vec2(5.0, 15.0)

        fake_clock.advance(0.5)
        assert anim.value == Vec2(10.0, 20.0)
    finally:
        observable_runtime.set_clock(prev_clock)


def test_animatable_retargets_in_flight() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        anim = Animatable(0.0, motion=LinearMotion(1.0))
        anim.target = 10.0
        fake_clock.advance(0.4)
        assert anim.value == 4.0

        anim.target = 20.0
        fake_clock.advance(0.5)
        assert anim.value == 12.0

        fake_clock.advance(0.5)
        assert anim.value == 20.0
    finally:
        observable_runtime.set_clock(prev_clock)


def test_spring_motion_works_for_multidimensional_vectors() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        anim = Animatable.vector(
            Vec2(0.0, 0.0),
            Vec2Converter(),
            motion=SpringMotion(stiffness=300.0, damping=40.0, mass=1.0),
        )
        anim.target = Vec2(10.0, -5.0)

        for _ in range(200):
            fake_clock.advance(1 / 60.0)

        assert abs(anim.value.x - 10.0) < 0.05
        assert abs(anim.value.y + 5.0) < 0.05
    finally:
        observable_runtime.set_clock(prev_clock)
