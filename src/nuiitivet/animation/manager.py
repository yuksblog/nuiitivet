"""Per-App animation manager."""

from __future__ import annotations

import logging
from typing import Callable, Dict, Set

from .animation import Animation
from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import runtime as observable_runtime


logger = logging.getLogger(__name__)


class AnimationManager:
    """Manage active animations for an App.

    The App should call ``manager.step(dt)`` each frame. The manager will
    update animations and call the application's ``invalidate`` once if any
    animation updated state during the frame.
    """

    def __init__(self, app: object) -> None:
        self._app = app
        self._anims: Set[Animation] = set()
        self._delay_wakeups: Dict[Animation, Callable[[float], None]] = {}

    def start(self, anim: Animation) -> "AnimationHandle":
        try:
            self._anims.add(anim)
        except Exception:
            exception_once(logger, "animation_manager_add_exc", "Failed to add animation to manager")

        self._schedule_delay_wakeup(anim)

        self._invalidate_app()

        return AnimationHandle(self, anim)

    def _schedule_delay_wakeup(self, anim: Animation) -> None:
        try:
            delay_s = float(getattr(anim, "delay", 0.0))
        except Exception:
            exception_once(logger, "animation_manager_delay_attr_exc", "Failed to read animation delay")
            delay_s = 0.0
        if delay_s <= 0.0:
            return

        # Avoid spawning background Timer threads during tests/headless runs.
        # A UI backend (e.g. pyglet) installs its own event-loop-driven clock.
        if observable_runtime.clock.__class__.__name__ == "_ThreadClock":
            return

        def _wakeup(_dt: float) -> None:
            try:
                self._delay_wakeups.pop(anim, None)
            except Exception:
                exception_once(logger, "animation_manager_delay_pop_exc", "Failed to pop delay wakeup callback")
            if anim not in self._anims:
                return
            try:
                if not anim.is_alive:
                    return
            except Exception:
                exception_once(logger, "animation_manager_is_alive_exc", "Failed to read animation is_alive")

            # End of delay should trigger at least one draw even under
            # on-demand rendering.
            self._invalidate_app(immediate=True)

        self._delay_wakeups[anim] = _wakeup
        try:
            observable_runtime.clock.schedule_once(_wakeup, delay_s)
        except Exception:
            try:
                self._delay_wakeups.pop(anim, None)
            except Exception:
                exception_once(
                    logger,
                    "animation_manager_schedule_cleanup_exc",
                    "Failed to clean up delay wakeup after schedule_once",
                )
            exception_once(logger, "animation_manager_schedule_once_exc", "clock.schedule_once failed")

    def _cancel_delay_wakeup(self, anim: Animation) -> None:
        cb = self._delay_wakeups.pop(anim, None)
        if cb is None:
            return
        try:
            observable_runtime.clock.unschedule(cb)
        except Exception:
            exception_once(logger, "animation_manager_unschedule_exc", "clock.unschedule failed")

    def cancel(self, anim: Animation) -> None:
        self._cancel_delay_wakeup(anim)
        if anim in self._anims:
            try:
                self._anims.remove(anim)
            except Exception:
                exception_once(logger, "animation_manager_remove_exc", "Failed to remove animation from manager")
        try:
            anim.cancel()
        except Exception:
            exception_once(logger, "animation_manager_anim_cancel_exc", "Animation.cancel failed")

    def _invalidate_app(self, immediate: bool = False) -> None:
        try:
            invalidate = getattr(self._app, "invalidate", None)
            if invalidate is not None:
                try:
                    invalidate(immediate=immediate)
                except TypeError:
                    invalidate()
        except Exception:
            exception_once(logger, "animation_manager_invalidate_exc", "App.invalidate failed")

    def step(self, dt: float) -> None:
        if not self._anims:
            return
        frame_advanced = False
        to_remove: list[Animation] = []
        for a in list(self._anims):
            prev_alive = a.is_alive
            prev_progress = a.progress
            try:
                alive = a.update(dt)
            except Exception:
                exception_once(logger, "animation_manager_update_exc", "Animation.update failed")
                alive = False
            try:
                new_progress = a.progress
            except Exception:
                exception_once(logger, "animation_manager_progress_exc", "Failed to read animation progress")
                new_progress = prev_progress
            if new_progress != prev_progress or (prev_alive and not alive):
                frame_advanced = True
                self._cancel_delay_wakeup(a)
            if not alive:
                to_remove.append(a)

        for a in to_remove:
            try:
                a.cancel()
            except Exception:
                exception_once(logger, "animation_manager_cancel_remove_exc", "Animation.cancel failed while removing")
            try:
                self._anims.remove(a)
            except Exception:
                exception_once(
                    logger,
                    "animation_manager_remove_to_remove_exc",
                    "Failed to remove animation during cleanup",
                )
            self._cancel_delay_wakeup(a)

        if frame_advanced:
            self._invalidate_app()

    def cancel_all(self) -> None:
        for a in list(self._anims):
            try:
                a.cancel()
            except Exception:
                exception_once(logger, "animation_manager_cancel_all_anim_exc", "Animation.cancel failed in cancel_all")
            self._cancel_delay_wakeup(a)
        try:
            self._anims.clear()
        except Exception:
            exception_once(logger, "animation_manager_clear_anims_exc", "Failed to clear animations set")

        try:
            self._delay_wakeups.clear()
        except Exception:
            exception_once(logger, "animation_manager_clear_wakeups_exc", "Failed to clear delay wakeups")

    def active_count(self) -> int:
        return len(self._anims)


class AnimationHandle:
    """Lightweight controller returned by AnimationManager.start."""

    def __init__(self, manager: AnimationManager, animation: Animation) -> None:
        self._manager = manager
        self._animation = animation

    @property
    def animation(self) -> Animation:
        return self._animation

    @property
    def progress(self) -> float:
        return self._animation.progress

    @property
    def is_running(self) -> bool:
        return self._animation.is_alive

    def pause(self) -> None:
        self._animation.pause()

    def resume(self) -> None:
        self._animation.resume()

    def cancel(self) -> None:
        self._manager.cancel(self._animation)

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self.is_running
