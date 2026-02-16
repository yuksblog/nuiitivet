"""Retargetable animation value container."""

from __future__ import annotations

from typing import Callable, Generic, Optional, TypeVar, Any, cast

from nuiitivet.observable.value import _ObservableValue
from nuiitivet.observable import runtime

from .converter import FloatConverter, VectorConverter
from .motion import Motion, MotionState

T = TypeVar("T")
V = TypeVar("V")


class Animatable(Generic[T]):
    """Declarative, retargetable animation value.

    Assign to ``target`` to retarget motion without reversing.
    ``value`` is read-only and reflects the current animated value.
    """

    def __init__(self: "Animatable[float]", initial_value: float, motion: Optional[Motion] = None) -> None:
        """Initialize float animatable value.

        Args:
            initial_value: Initial float value.
            motion: Optional motion model. If omitted, target assignment updates immediately.
        """
        value = float(initial_value)
        converter: VectorConverter[float] = FloatConverter()
        self._initialize(initial_value=value, converter=converter, motion=motion)

    @staticmethod
    def vector(
        initial_value: V,
        converter: VectorConverter[V],
        motion: Optional[Motion] = None,
    ) -> "Animatable[V]":
        """Initialize vector-converted animatable value.

        Args:
            initial_value: Initial value.
            converter: Value/vector converter.
            motion: Optional motion model. If omitted, target assignment updates immediately.
        """
        instance = cast("Animatable[V]", object.__new__(Animatable))
        instance._initialize(initial_value=initial_value, converter=converter, motion=motion)
        return instance

    def _initialize(self, initial_value: T, converter: VectorConverter[T], motion: Optional[Motion]) -> None:
        self._converter = converter
        self._value = _ObservableValue(initial_value)
        self._target = initial_value
        self._motion = motion
        self._state: Optional[MotionState] = None
        self._ticker: Optional[Callable[[float], None]] = None

        if self._motion is not None:
            initial_vector = self._converter.to_vector(initial_value)
            self._state = self._motion.create_state(initial_vector, initial_vector)

    @property
    def value(self) -> T:
        return self._value.value

    @property
    def target(self) -> T:
        return self._target

    @target.setter
    def target(self, value: T) -> None:
        next_target = value
        self._target = next_target

        if self._motion is None:
            self._value.value = next_target
            return

        target_vector = self._converter.to_vector(next_target)

        if self._state is None:
            current_vector = self._converter.to_vector(self.value)
            self._state = self._motion.create_state(current_vector, target_vector)
        else:
            self._motion.retarget(self._state, target_vector)

        self._start_ticking()

    def stop(self) -> None:
        """Stop any active motion and keep the current value."""
        self._stop_ticking()
        self._target = self.value
        if self._state is not None:
            current_vector = self._converter.to_vector(self.value)
            self._state.value = current_vector.copy()
            self._state.start = current_vector.copy()
            self._state.target = current_vector.copy()
            self._state.velocity = [0.0 for _ in current_vector]
            self._state.done = True

    def subscribe(self, cb: Callable[[T], None]):
        return self._value.subscribe(cb)

    def changes(self):
        return self._value.changes()

    def map(self, transform: Callable[[T], Any]):
        return self._value.map(transform)

    def _start_ticking(self) -> None:
        if self._ticker is not None:
            return
        ticker = self._tick
        runtime.clock.schedule_interval(ticker, 1 / 60.0)
        self._ticker = ticker

    def _stop_ticking(self) -> None:
        if self._ticker is None:
            return
        runtime.clock.unschedule(self._ticker)
        self._ticker = None

    def _tick(self, dt: float) -> None:
        if self._motion is None or self._state is None:
            self._stop_ticking()
            return

        done = self._motion.step(self._state, dt)
        self._value.value = self._converter.from_vector(self._state.value)

        if done:
            self._value.value = self._converter.from_vector(self._state.target)
            self._state.value = self._state.target.copy()
            self._state.done = True
            self._stop_ticking()


__all__ = ["Animatable"]
