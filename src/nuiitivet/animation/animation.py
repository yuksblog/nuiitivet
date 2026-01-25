"""Time-based animation primitive."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from nuiitivet.common.logging_once import exception_once

from .easing import ease_cubic_out


_logger = logging.getLogger(__name__)


class Animation:
    """A simple time-based animation.

    Args:
        duration: length of the animated portion in seconds (>= 0)
        on_update: callable(progress: float) where progress in [0,1]
        easing: easing function mapping [0,1] -> [0,1]
        delay: time in seconds to wait before starting the animated portion
        on_complete: optional callable() invoked when animation finishes
    """

    def __init__(
        self,
        duration: float,
        on_update: Callable[[float], None],
        *,
        easing: Callable[[float], float] = ease_cubic_out,
        delay: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        self.duration = max(0.0, float(duration))
        self.on_update = on_update
        self.easing = easing
        self.delay = max(0.0, float(delay))
        self.on_complete = on_complete

        self._elapsed = 0.0
        self._alive = True
        self._paused = False
        self._delay_notified = False

        self._emit_progress(0.0)
        if self.delay > 0.0:
            self._delay_notified = True

    @property
    def is_alive(self) -> bool:
        return self._alive

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def progress(self) -> float:
        if self.duration <= 0.0:
            return 1.0 if not self._alive else 0.0
        active_time = max(0.0, self._elapsed - self.delay)
        return max(0.0, min(1.0, active_time / self.duration))

    def pause(self) -> None:
        if self._alive:
            self._paused = True

    def resume(self) -> None:
        if self._alive:
            self._paused = False

    def _emit_progress(self, value: float) -> None:
        try:
            self.on_update(value)
        except Exception:
            exception_once(_logger, "animation_on_update_exc", "Animation on_update callback raised")

    def _emit_complete(self) -> None:
        if self.on_complete is None:
            return
        try:
            self.on_complete()
        except Exception:
            exception_once(_logger, "animation_on_complete_exc", "Animation on_complete callback raised")

    def update(self, dt: float) -> bool:
        """Advance the animation by dt seconds. Returns True if still alive."""

        if not self._alive:
            return False
        if self._paused:
            return True
        self._elapsed += float(dt)

        if self._elapsed < self.delay:
            if not self._delay_notified:
                self._emit_progress(0.0)
                self._delay_notified = True
            return True

        if self.duration <= 0.0:
            t = 1.0
        else:
            active = max(0.0, self._elapsed - self.delay)
            t = min(1.0, active / max(self.duration, 1e-9))

        try:
            eased = self.easing(t)
        except Exception:
            eased = t

        self._emit_progress(eased)

        if t >= 1.0:
            self._alive = False
            self._emit_complete()

        return self._alive

    def cancel(self) -> None:
        self._alive = False
        self._paused = False
