"""Retargetable animation value container."""

from __future__ import annotations

from typing import Callable, Optional, TypeVar, Any

from nuiitivet.observable.value import _ObservableValue
from nuiitivet.observable import runtime

from .motion import Motion, MotionState
from .tween import Tween

T = TypeVar("T")


class DrivenAnimatable(_ObservableValue[T]):
    """Observable derived from an Animatable using a Tween."""

    def __init__(self, parent: "Animatable", tween: Tween[T]) -> None:
        super().__init__(tween.transform(parent.value))
        self._parent = parent
        self._tween = tween
        parent.subscribe(self._on_parent_change)

    def _on_parent_change(self, value: float) -> None:
        self.value = self._tween.transform(value)


class Animatable:
    """Declarative, retargetable animation value.

    Assign to ``target`` to retarget motion without reversing.
    ``value`` is read-only and reflects the current animated value.
    """

    def __init__(self, initial: float) -> None:
        self._value = _ObservableValue(float(initial))
        self._target = float(initial)
        self._motion: Optional[Motion] = None
        self._state: Optional[MotionState] = None
        self._ticker: Optional[Callable[[float], None]] = None

    @property
    def value(self) -> float:
        return float(self._value.value)

    @property
    def target(self) -> float:
        return float(self._target)

    @target.setter
    def target(self, value: float) -> None:
        next_target = float(value)
        self._target = next_target

        if self._motion is None:
            self._value.value = next_target
            return

        if self._state is None:
            self._state = self._motion.create_state(self.value, next_target)
        else:
            self._motion.retarget(self._state, next_target)

        self._start_ticking()

    def drive(self, spec: Motion, tween: Optional[Tween[T]] = None) -> DrivenAnimatable[T]:
        """Create a derived observable driven by ``spec`` and mapped by ``tween``."""
        self._set_motion(spec)
        real_tween: Tween[Any] = tween if tween is not None else Tween()
        return DrivenAnimatable(self, real_tween)

    def stop(self) -> None:
        """Stop any active motion and keep the current value."""
        self._stop_ticking()
        self._target = self.value
        if self._state is not None:
            self._state.value = self.value
            self._state.target = self._target
            self._state.velocity = 0.0
            self._state.done = True

    def subscribe(self, cb: Callable[[float], None]):
        return self._value.subscribe(cb)

    def changes(self):
        return self._value.changes()

    def map(self, transform: Callable[[float], Any]):
        return self._value.map(transform)

    def _set_motion(self, spec: Motion) -> None:
        if self._motion is spec:
            return

        self._motion = spec
        if self._state is None:
            self._state = spec.create_state(self.value, self._target)
        else:
            self._state = spec.create_state(self._state.value, self._target)

        if self._target != self.value:
            self._start_ticking()

    def _start_ticking(self) -> None:
        if self._ticker is not None:
            return
        runtime.clock.schedule_interval(self._tick, 1 / 60.0)
        self._ticker = self._tick

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
        self._value.value = float(self._state.value)

        if done:
            self._value.value = float(self._state.target)
            self._state.value = float(self._state.target)
            self._state.done = True
            self._stop_ticking()


__all__ = ["Animatable", "DrivenAnimatable"]
