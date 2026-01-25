"""Animation and invalidation helpers."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Protocol

from nuiitivet.common.logging_once import exception_once

logger = logging.getLogger(__name__)


class AnimationHandleLike(Protocol):
    @property
    def is_running(self) -> bool: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def cancel(self) -> None: ...


class AnimationHostMixin:
    """Provides invalidate/animate utilities delegated to the App."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[override]
        super().__init__(*args, **kwargs)

    # --- Invalidation ------------------------------------------------------
    def invalidate(self, immediate: bool = False) -> None:
        app = getattr(self, "_app", None)
        if app is None:
            return
        try:
            app.invalidate(immediate=immediate)
        except TypeError:
            try:
                app.invalidate()
            except Exception:
                exception_once(
                    logger,
                    f"animation_host_invalidate_fallback_exc:{type(app).__name__}",
                    "App.invalidate() fallback call raised for app=%s",
                    type(app).__name__,
                )
        except Exception:
            exception_once(
                logger,
                f"animation_host_invalidate_exc:{type(app).__name__}",
                "App.invalidate(immediate=%s) raised for app=%s",
                immediate,
                type(app).__name__,
            )

    # --- Animation ---------------------------------------------------------
    def animate(
        self,
        *,
        duration: float,
        on_update: Callable[[float], None],
        delay: float = 0.0,
        easing: Optional[Callable[[float], float]] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> "AnimationHandleLike":
        app = getattr(self, "_app", None)
        if app is None:
            raise RuntimeError("Widget.animate() requires the widget to be mounted into an App.")
        kwargs: dict[str, Any] = dict(duration=duration, on_update=on_update, delay=delay, on_complete=on_complete)
        if easing is not None:
            kwargs["easing"] = easing
        return app.animate(**kwargs)

    def animate_value(
        self,
        *,
        target: float,
        duration: float,
        start: Optional[float] = None,
        delay: float = 0.0,
        easing: Optional[Callable[[float], float]] = None,
        attr: Optional[str] = None,
        apply: Optional[Callable[[float], None]] = None,
        invalidate: bool = True,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> "AnimationHandleLike":
        if attr is None and apply is None:
            raise ValueError("Provide either 'attr' or 'apply' to animate_value().")
        if attr is not None and apply is not None:
            raise ValueError("Specify only one of 'attr' or 'apply'.")

        if attr is not None:

            def setter(value: float) -> None:
                setattr(self, attr, value)

        else:
            assert apply is not None

            def setter(value: float) -> None:
                apply(value)

        if start is None:
            if attr is None:
                raise ValueError("'start' must be provided when no attribute binding is supplied.")
            current = getattr(self, attr)
            start_value = float(current)
        else:
            start_value = float(start)
        end_value = float(target)

        def _apply(progress: float) -> None:
            value = start_value + (end_value - start_value) * progress
            setter(value)
            if invalidate:
                self.invalidate()

        return self.animate(
            duration=duration,
            on_update=_apply,
            delay=delay,
            easing=easing,
            on_complete=on_complete,
        )
