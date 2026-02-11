"""Declarative motion models for retargetable animation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class MotionState:
    """Mutable motion state used by Motion.

    Attributes:
        value: Current animated value.
        target: Current target value.
        start: Start value used by time-based specs.
        elapsed: Elapsed time in seconds.
        velocity: Current velocity for physics-based specs.
        done: Whether the motion has reached its target.
    """

    value: float
    target: float
    start: float
    elapsed: float
    velocity: float = 0.0
    done: bool = False


class Motion(Protocol):
    """Protocol for declarative motion.

    Motion specs are responsible for advancing MotionState over time
    and handling retargeting without pausing.
    """

    def create_state(self, value: float, target: float) -> MotionState: ...

    def step(self, state: MotionState, dt: float) -> bool: ...

    def retarget(self, state: MotionState, target: float) -> None: ...


class LinearMotion:
    """Linear time-based motion.

    Args:
        duration: Duration in seconds for a full transition.
    """

    def __init__(self, duration: float) -> None:
        self.duration = max(0.0, float(duration))

    def create_state(self, value: float, target: float) -> MotionState:
        return MotionState(value=float(value), target=float(target), start=float(value), elapsed=0.0)

    def retarget(self, state: MotionState, target: float) -> None:
        state.start = float(state.value)
        state.target = float(target)
        state.elapsed = 0.0
        state.done = False

    def step(self, state: MotionState, dt: float) -> bool:
        duration = self.duration
        if duration <= 0.0:
            state.value = float(state.target)
            state.done = True
            return True

        state.elapsed += max(0.0, float(dt))
        progress = min(1.0, state.elapsed / max(duration, 1e-9))
        state.value = state.start + (state.target - state.start) * progress
        state.done = progress >= 1.0
        return state.done


class BezierMotion:
    """Bezier time-based motion.

    Args:
        x1: Control point 1 x.
        y1: Control point 1 y.
        x2: Control point 2 x.
        y2: Control point 2 y.
        duration: Duration in seconds for a full transition.
    """

    def __init__(self, x1: float, y1: float, x2: float, y2: float, duration: float) -> None:
        self.duration = max(0.0, float(duration))
        self._curve = _CubicBezier(float(x1), float(y1), float(x2), float(y2))

    def create_state(self, value: float, target: float) -> MotionState:
        return MotionState(value=float(value), target=float(target), start=float(value), elapsed=0.0)

    def retarget(self, state: MotionState, target: float) -> None:
        state.start = float(state.value)
        state.target = float(target)
        state.elapsed = 0.0
        state.done = False

    def step(self, state: MotionState, dt: float) -> bool:
        duration = self.duration
        if duration <= 0.0:
            state.value = float(state.target)
            state.done = True
            return True

        state.elapsed += max(0.0, float(dt))
        progress = min(1.0, state.elapsed / max(duration, 1e-9))
        eased = self._curve.transform(progress)
        state.value = state.start + (state.target - state.start) * eased
        state.done = progress >= 1.0
        return state.done


class SpringMotion:
    """Spring-based motion.

    Args:
        stiffness: Spring stiffness constant.
        damping: Damping coefficient.
        mass: Mass attached to the spring.
        initial_velocity: Initial velocity in units per second.
    """

    def __init__(
        self,
        stiffness: float,
        damping: float,
        mass: float,
        *,
        initial_velocity: float = 0.0,
        tolerance: float = 1e-3,
    ) -> None:
        self.stiffness = float(stiffness)
        self.damping = float(damping)
        self.mass = max(1e-9, float(mass))
        self.initial_velocity = float(initial_velocity)
        self.tolerance = max(0.0, float(tolerance))

    def create_state(self, value: float, target: float) -> MotionState:
        return MotionState(
            value=float(value),
            target=float(target),
            start=float(value),
            elapsed=0.0,
            velocity=float(self.initial_velocity),
        )

    def retarget(self, state: MotionState, target: float) -> None:
        state.target = float(target)
        state.done = False

    def step(self, state: MotionState, dt: float) -> bool:
        dt = max(0.0, float(dt))
        if dt <= 0.0:
            return state.done

        displacement = state.value - state.target
        acceleration = (-self.stiffness * displacement - self.damping * state.velocity) / self.mass
        state.velocity += acceleration * dt
        state.value += state.velocity * dt
        state.elapsed += dt

        if abs(state.velocity) <= self.tolerance and abs(state.value - state.target) <= self.tolerance:
            state.value = float(state.target)
            state.velocity = 0.0
            state.done = True

        return state.done


class _CubicBezier:
    """Cubic Bezier easing helper for BezierMotion."""

    def __init__(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self._x1 = float(x1)
        self._y1 = float(y1)
        self._x2 = float(x2)
        self._y2 = float(y2)

    def _sample_curve_x(self, t: float) -> float:
        return (
            (3.0 * self._x1 - 3.0 * self._x2 + 1.0) * t * t * t
            + (3.0 * self._x2 - 6.0 * self._x1) * t * t
            + (3.0 * self._x1) * t
        )

    def _sample_curve_y(self, t: float) -> float:
        return (
            (3.0 * self._y1 - 3.0 * self._y2 + 1.0) * t * t * t
            + (3.0 * self._y2 - 6.0 * self._y1) * t * t
            + (3.0 * self._y1) * t
        )

    def _sample_curve_derivative_x(self, t: float) -> float:
        return (
            (9.0 * self._x1 - 9.0 * self._x2 + 3.0) * t * t + (6.0 * self._x2 - 12.0 * self._x1) * t + (3.0 * self._x1)
        )

    def transform(self, t: float) -> float:
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0

        u = t
        for _ in range(8):
            x = self._sample_curve_x(u) - t
            dx = self._sample_curve_derivative_x(u)
            if abs(dx) < 1e-6:
                break
            u -= x / dx
            if u < 0.0 or u > 1.0:
                u = min(1.0, max(0.0, u))
                break

        if abs(self._sample_curve_x(u) - t) > 1e-5:
            low = 0.0
            high = 1.0
            u = t
            for _ in range(12):
                x = self._sample_curve_x(u)
                if x < t:
                    low = u
                else:
                    high = u
                u = (low + high) * 0.5

        return self._sample_curve_y(u)


__all__ = [
    "MotionState",
    "Motion",
    "LinearMotion",
    "BezierMotion",
    "SpringMotion",
]
