"""Declarative motion models for retargetable animation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass
class MotionState:
    """Mutable motion state used by Motion.

    Attributes:
        value: Current animated vector value.
        target: Current target vector value.
        start: Start vector used by time-based specs.
        elapsed: Elapsed time in seconds.
        velocity: Current vector velocity for physics-based specs.
        done: Whether the motion has reached its target.
    """

    value: list[float]
    target: list[float]
    start: list[float]
    elapsed: float
    velocity: list[float]
    done: bool = False

    def __post_init__(self) -> None:
        dim = len(self.value)
        if len(self.target) != dim or len(self.start) != dim or len(self.velocity) != dim:
            raise ValueError("MotionState vectors must have the same dimension")


def _copy_vector(value: Sequence[float]) -> list[float]:
    return [float(v) for v in value]


def _assert_same_dimension(lhs: Sequence[float], rhs: Sequence[float], *, message: str) -> None:
    if len(lhs) != len(rhs):
        raise ValueError(message)


class Motion(Protocol):
    """Protocol for declarative motion.

    Motion specs are responsible for advancing MotionState over time
    and handling retargeting without pausing.
    """

    def create_state(self, value: list[float], target: list[float]) -> MotionState: ...

    def step(self, state: MotionState, dt: float) -> bool: ...

    def retarget(self, state: MotionState, target: list[float]) -> None: ...


class LinearMotion:
    """Linear time-based motion.

    Args:
        duration: Duration in seconds for a full transition.
    """

    def __init__(self, duration: float) -> None:
        self.duration = max(0.0, float(duration))

    def create_state(self, value: list[float], target: list[float]) -> MotionState:
        _assert_same_dimension(value, target, message="LinearMotion requires value/target dimensions to match")
        value_vec = _copy_vector(value)
        target_vec = _copy_vector(target)
        return MotionState(
            value=value_vec,
            target=target_vec,
            start=value_vec.copy(),
            elapsed=0.0,
            velocity=[0.0 for _ in value_vec],
        )

    def retarget(self, state: MotionState, target: list[float]) -> None:
        _assert_same_dimension(state.value, target, message="LinearMotion retarget dimension mismatch")
        state.start = state.value.copy()
        state.target = _copy_vector(target)
        state.elapsed = 0.0
        state.done = False

    def step(self, state: MotionState, dt: float) -> bool:
        duration = self.duration
        if duration <= 0.0:
            state.value = state.target.copy()
            state.done = True
            return True

        state.elapsed += max(0.0, float(dt))
        progress = min(1.0, state.elapsed / max(duration, 1e-9))
        state.value = [
            start + (target - start) * progress for start, target in zip(state.start, state.target, strict=True)
        ]
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

    def create_state(self, value: list[float], target: list[float]) -> MotionState:
        _assert_same_dimension(value, target, message="BezierMotion requires value/target dimensions to match")
        value_vec = _copy_vector(value)
        target_vec = _copy_vector(target)
        return MotionState(
            value=value_vec,
            target=target_vec,
            start=value_vec.copy(),
            elapsed=0.0,
            velocity=[0.0 for _ in value_vec],
        )

    def retarget(self, state: MotionState, target: list[float]) -> None:
        _assert_same_dimension(state.value, target, message="BezierMotion retarget dimension mismatch")
        state.start = state.value.copy()
        state.target = _copy_vector(target)
        state.elapsed = 0.0
        state.done = False

    def step(self, state: MotionState, dt: float) -> bool:
        duration = self.duration
        if duration <= 0.0:
            state.value = state.target.copy()
            state.done = True
            return True

        state.elapsed += max(0.0, float(dt))
        progress = min(1.0, state.elapsed / max(duration, 1e-9))
        eased = self._curve.transform(progress)
        state.value = [
            start + (target - start) * eased for start, target in zip(state.start, state.target, strict=True)
        ]
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
        initial_velocity: float | Sequence[float] = 0.0,
        tolerance: float = 1e-3,
    ) -> None:
        self.stiffness = float(stiffness)
        self.damping = float(damping)
        self.mass = max(1e-9, float(mass))
        self.initial_velocity = initial_velocity
        self.tolerance = max(0.0, float(tolerance))

    def _make_initial_velocity(self, dimension: int) -> list[float]:
        if isinstance(self.initial_velocity, Sequence) and not isinstance(self.initial_velocity, (str, bytes)):
            initial_velocity = _copy_vector(self.initial_velocity)
            if len(initial_velocity) == 1 and dimension > 1:
                return [initial_velocity[0] for _ in range(dimension)]
            if len(initial_velocity) != dimension:
                raise ValueError("SpringMotion initial_velocity dimension mismatch")
            return initial_velocity

        scalar = float(self.initial_velocity)
        return [scalar for _ in range(dimension)]

    def create_state(self, value: list[float], target: list[float]) -> MotionState:
        _assert_same_dimension(value, target, message="SpringMotion requires value/target dimensions to match")
        value_vec = _copy_vector(value)
        target_vec = _copy_vector(target)
        return MotionState(
            value=value_vec,
            target=target_vec,
            start=value_vec.copy(),
            elapsed=0.0,
            velocity=self._make_initial_velocity(len(value_vec)),
        )

    def retarget(self, state: MotionState, target: list[float]) -> None:
        _assert_same_dimension(state.value, target, message="SpringMotion retarget dimension mismatch")
        state.target = _copy_vector(target)
        state.done = False

    def step(self, state: MotionState, dt: float) -> bool:
        dt = max(0.0, float(dt))
        if dt <= 0.0:
            return state.done

        next_velocity: list[float] = []
        next_value: list[float] = []
        for value, target, velocity in zip(state.value, state.target, state.velocity, strict=True):
            displacement = value - target
            acceleration = (-self.stiffness * displacement - self.damping * velocity) / self.mass
            velocity = velocity + acceleration * dt
            value = value + velocity * dt
            next_velocity.append(velocity)
            next_value.append(value)

        state.velocity = next_velocity
        state.value = next_value
        state.elapsed += dt

        velocity_stable = all(abs(v) <= self.tolerance for v in state.velocity)
        position_stable = all(
            abs(v - target) <= self.tolerance for v, target in zip(state.value, state.target, strict=True)
        )
        if velocity_stable and position_stable:
            state.value = state.target.copy()
            state.velocity = [0.0 for _ in state.velocity]
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
