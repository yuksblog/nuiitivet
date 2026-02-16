"""Material-specific navigation visual mapping and composition."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from nuiitivet.common.logging_once import exception_once
from nuiitivet.navigation.layer_composer import NavigationLayerComposer, NavigationLayerCompositionContext
from nuiitivet.navigation.transition_spec import TransitionPhase, TransitionSpec
from nuiitivet.rendering.skia.color import make_opacity_paint
from nuiitivet.widgeting.widget import Widget

from .transition_visual_spec import resolve_material_transition_visual_spec


logger = logging.getLogger(__name__)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _paint_widget_with_visual_params(
    canvas: Any,
    widget: Widget,
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    opacity: float,
    scale: tuple[float, float],
    translation: tuple[float, float],
) -> None:
    clamped_opacity = _clamp01(opacity)
    sx, sy = scale
    dx, dy = translation

    if canvas is None:
        widget.paint(canvas, x, y, width, height)
        return

    needs_opacity = clamped_opacity < 1.0
    needs_transform = (float(dx), float(dy)) != (0.0, 0.0) or (float(sx), float(sy)) != (1.0, 1.0)

    if not needs_opacity and not needs_transform:
        widget.paint(canvas, x, y, width, height)
        return

    saved_outer = False
    saved_layer = False
    try:
        if hasattr(canvas, "save"):
            canvas.save()
            saved_outer = True

        if needs_opacity:
            layer_paint = make_opacity_paint(clamped_opacity)
            if layer_paint is not None and hasattr(canvas, "saveLayer"):
                canvas.saveLayer(None, layer_paint)
                saved_layer = True

        if needs_transform:
            if (float(dx), float(dy)) != (0.0, 0.0) and hasattr(canvas, "translate"):
                canvas.translate(float(dx), float(dy))

            if (float(sx), float(sy)) != (1.0, 1.0) and hasattr(canvas, "translate") and hasattr(canvas, "scale"):
                ox = float(x) + (float(width) / 2.0)
                oy = float(y) + (float(height) / 2.0)
                canvas.translate(ox, oy)
                canvas.scale(float(sx), float(sy))
                canvas.translate(-ox, -oy)

        widget.paint(canvas, x, y, width, height)
    except Exception:
        exception_once(
            logger,
            "material_navigation_layer_paint_exc",
            "Material navigation layer paint raised",
        )
        widget.paint(canvas, x, y, width, height)
    finally:
        if saved_layer:
            try:
                canvas.restore()
            except Exception:
                pass
        if saved_outer:
            try:
                canvas.restore()
            except Exception:
                pass


@dataclass(frozen=True, slots=True)
class NavigationVisualState:
    """Material visual parameters for one navigation transition frame."""

    content_opacity: float
    content_scale: tuple[float, float]
    content_translation: tuple[float, float]


class MaterialNavigationVisualMapper:
    """Maps lifecycle transitions to Material navigation visual state."""

    def map_lifecycle(
        self,
        transition_spec: TransitionSpec,
        *,
        phase: TransitionPhase,
        progress: float,
    ) -> NavigationVisualState:
        """Convert lifecycle inputs to Material visual parameters."""
        visual = resolve_material_transition_visual_spec(
            transition_spec,
            phase=phase,
            progress=progress,
        )
        return NavigationVisualState(
            content_opacity=float(visual.content_opacity),
            content_scale=visual.content_scale,
            content_translation=visual.content_translation,
        )


class MaterialNavigationLayerComposer(NavigationLayerComposer):
    """Material implementation of navigation transition composition."""

    def __init__(self, mapper: MaterialNavigationVisualMapper | None = None) -> None:
        self._mapper = mapper or MaterialNavigationVisualMapper()

    def paint_static(self, *, canvas: Any, widget: Widget, x: int, y: int, width: int, height: int) -> None:
        widget.paint(canvas, x, y, width, height)

    def paint_transition(self, context: NavigationLayerCompositionContext) -> None:
        from_state = self._mapper.map_lifecycle(
            context.from_transition_spec,
            phase=context.from_phase,
            progress=context.progress,
        )
        to_state = self._mapper.map_lifecycle(
            context.to_transition_spec,
            phase=context.to_phase,
            progress=context.progress,
        )
        self._paint_with_visual_state(
            context.canvas,
            context.from_widget,
            context.x,
            context.y,
            context.width,
            context.height,
            state=from_state,
        )
        self._paint_with_visual_state(
            context.canvas,
            context.to_widget,
            context.x,
            context.y,
            context.width,
            context.height,
            state=to_state,
        )

    def _paint_with_visual_state(
        self,
        canvas: Any,
        widget: Widget,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        state: NavigationVisualState,
    ) -> None:
        _paint_widget_with_visual_params(
            canvas,
            widget,
            x,
            y,
            width,
            height,
            opacity=state.content_opacity,
            scale=state.content_scale,
            translation=state.content_translation,
        )


__all__ = [
    "NavigationVisualState",
    "MaterialNavigationVisualMapper",
    "MaterialNavigationLayerComposer",
]
