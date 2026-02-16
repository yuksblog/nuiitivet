from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from nuiitivet.animation import Animatable, BezierMotion, Motion
from nuiitivet.widgeting.widget_animation import AnimationHandleLike


@dataclass(frozen=True, slots=True)
class TransitionMotionPreset:
    """Motion preset used by transition engine."""

    duration_sec: float
    x1: float
    y1: float
    x2: float
    y2: float

    def create_motion(self) -> Motion:
        return BezierMotion(self.x1, self.y1, self.x2, self.y2, self.duration_sec)


class TransitionMotions:
    """Centralized transition motion presets."""

    @staticmethod
    def navigation_default() -> TransitionMotionPreset:
        # Keep current behavior duration while moving to Animatable runtime.
        return TransitionMotionPreset(duration_sec=0.6, x1=0.2, y1=0.0, x2=0.0, y2=1.0)


class _TransitionAnimHandle(AnimationHandleLike):
    def __init__(self, engine: "TransitionEngine", token: int) -> None:
        self._engine = engine
        self._token = token

    @property
    def is_running(self) -> bool:
        return self._engine._is_running(self._token)

    def pause(self) -> None:
        # Animatable currently has no pause API.
        return

    def resume(self) -> None:
        # Animatable currently has no pause API.
        return

    def cancel(self) -> None:
        self._engine.cancel(token=self._token)


class TransitionEngine:
    """Animatable-backed transition driver with deterministic completion."""

    def __init__(self, *, preset: TransitionMotionPreset | None = None, epsilon: float = 1e-4) -> None:
        self._preset = preset or TransitionMotions.navigation_default()
        self._epsilon = abs(float(epsilon))

        self._token_counter: int = 0
        self._active_token: int | None = None
        self._target: float = 0.0

        self._anim: Animatable[float] | None = None
        self._unsubscribe: Optional[object] = None

        self._apply: Callable[[float], None] | None = None
        self._on_complete: Callable[[], None] | None = None

    def start(
        self,
        *,
        start: float,
        target: float,
        apply: Callable[[float], None],
        on_complete: Callable[[], None] | None = None,
        motion: Motion | None = None,
        restart: bool = True,
    ) -> AnimationHandleLike:
        """Start or retarget a transition animation.

        Args:
            start: Start value.
            target: Target value (0.0 or 1.0).
            apply: Callback to apply value.
            on_complete: Callback on completion.
            motion: Optional specific motion to use. If provided, animation is forced to restart with this motion.
            restart: Whether to force a restart from start value.
        """
        # If a specific motion is requested, we must reset the animatable to use it.
        motion_changed = motion is not None
        should_restart = restart or self._anim is None or motion_changed

        if should_restart:
            self._reset_anim(float(start), motion=motion)

        self._token_counter += 1
        token = self._token_counter
        self._active_token = token

        self._apply = apply
        self._on_complete = on_complete
        self._target = float(target)

        anim = self._anim
        assert anim is not None

        if abs(float(anim.value) - self._target) <= self._epsilon:
            self._emit_value(float(anim.value))
            self._finish_if_active(token)
        else:
            anim.target = self._target

        return _TransitionAnimHandle(self, token)

    def cancel(self, *, token: int | None = None) -> None:
        if token is not None and token != self._active_token:
            return

        if self._anim is not None:
            self._anim.stop()
        self._active_token = None

    def dispose(self) -> None:
        self.cancel()
        unsubscribe = self._unsubscribe
        self._unsubscribe = None
        if unsubscribe is None:
            return
        dispose = getattr(unsubscribe, "dispose", None)
        if callable(dispose):
            dispose()

    def _reset_anim(self, start: float, motion: Motion | None = None) -> None:
        self.cancel()
        anim_motion = motion or self._preset.create_motion()
        self._anim = Animatable(float(start), motion=anim_motion)

        unsubscribe = self._unsubscribe
        if unsubscribe is not None:
            dispose = getattr(unsubscribe, "dispose", None)
            if callable(dispose):
                dispose()

        self._unsubscribe = self._anim.subscribe(self._on_value)

    def _on_value(self, value: float) -> None:
        self._emit_value(float(value))

        active = self._active_token
        if active is None:
            return

        if abs(float(value) - self._target) <= self._epsilon:
            self._finish_if_active(active)

    def _emit_value(self, value: float) -> None:
        apply = self._apply
        if apply is None:
            return
        apply(float(value))

    def _finish_if_active(self, token: int) -> None:
        if token != self._active_token:
            return

        self._active_token = None
        on_complete = self._on_complete
        self._on_complete = None
        if on_complete is not None:
            on_complete()

    def _is_running(self, token: int) -> bool:
        return self._active_token == token


__all__ = ["TransitionEngine", "TransitionMotionPreset", "TransitionMotions"]
