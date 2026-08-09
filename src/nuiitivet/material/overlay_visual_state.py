"""Material-specific overlay visual mapping and composition."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.layout.container import Container
from nuiitivet.modifiers import opacity, scale, translate
from nuiitivet.modifiers.background import background
from nuiitivet.navigation.transition_state import TransitionLifecycle
from nuiitivet.observable import combine
from nuiitivet.overlay.layer_composer import (
    OverlayLayerComposer,
    OverlayLayerCompositionContext,
    OverlayLayerPaint,
)
from nuiitivet.widgeting.widget import Widget

from .theme.color_role import ColorRole
from .transition_visual_spec import resolve_material_transition_visual_spec


def _resolve_content_translation(state: "OverlayVisualState", content: Widget) -> tuple[float, float]:
    """Resolve pixel translation, incorporating any fractional components.

    Fractional values are multiplied by the content widget's current allocated
    dimensions.  Uses ``layout_rect`` first (available after the layout pass)
    and falls back to ``preferred_size`` for the very first frame.
    """
    tx, ty = state.content_translation
    fx, fy = state.content_translation_fraction
    if fx != 0.0 or fy != 0.0:
        rect = getattr(content, "layout_rect", None)
        if rect is not None:
            _, _, w, h = rect
        else:
            w, h = content.preferred_size()
        tx += fx * float(w)
        ty += fy * float(h)
    return (tx, ty)


@dataclass(frozen=True, slots=True)
class OverlayVisualState:
    """Material visual parameters for one overlay transition frame."""

    content_opacity: float
    content_scale: tuple[float, float]
    content_translation: tuple[float, float]
    content_translation_fraction: tuple[float, float]
    barrier_opacity: float | None


class MaterialOverlayVisualMapper:
    """Maps lifecycle transitions to Material overlay visual state."""

    def map_lifecycle(
        self,
        context: OverlayLayerCompositionContext,
        lifecycle: TransitionLifecycle,
    ) -> OverlayVisualState:
        """Convert lifecycle inputs to Material visual parameters."""
        visual = resolve_material_transition_visual_spec(
            context.transition_state.transition_spec,
            phase=lifecycle.phase,
            progress=lifecycle.progress,
        )
        return OverlayVisualState(
            content_opacity=float(visual.content_opacity),
            content_scale=visual.content_scale,
            content_translation=visual.content_translation,
            content_translation_fraction=visual.content_translation_fraction,
            barrier_opacity=visual.barrier_opacity,
        )


class MaterialOverlayLayerComposer(OverlayLayerComposer):
    """Material implementation of overlay layer composition.

    Painting only. Stacking, pointer blocking and outside-tap dismissal are
    applied by :meth:`Overlay.show` around what this returns, so nothing here
    stacks layers, does hit-testing, or branches on ``passthrough``.
    """

    # MD3 defines the scrim as a colour token; the opacity at which it is laid
    # over the content is this component's own business.
    _SCRIM_OPACITY = 0.5

    def __init__(self, mapper: MaterialOverlayVisualMapper | None = None) -> None:
        self._mapper = mapper or MaterialOverlayVisualMapper()

    def compose(self, context: OverlayLayerCompositionContext) -> OverlayLayerPaint:
        lifecycle_obs = context.transition_state.lifecycle_obs
        visual_obs = combine(lifecycle_obs).compute(lambda lifecycle: self._mapper.map_lifecycle(context, lifecycle))

        content_opacity_obs = combine(visual_obs).compute(lambda state: state.content_opacity)
        content_scale_obs = combine(visual_obs).compute(lambda state: state.content_scale)
        content_translation_obs = combine(visual_obs).compute(
            lambda state: _resolve_content_translation(state, context.content)
        )
        barrier_opacity_obs = combine(visual_obs).compute(
            lambda state: 1.0 if state.barrier_opacity is None else state.barrier_opacity
        )

        animated_content = context.content.modifier(
            opacity(content_opacity_obs) | scale(content_scale_obs) | translate(content_translation_obs)
        )
        backdrop: Widget | None = None
        if context.backdrop:
            backdrop = Container(width="wt", height="wt").modifier(
                background((ColorRole.SCRIM, self._SCRIM_OPACITY)) | opacity(barrier_opacity_obs)
            )

        return OverlayLayerPaint(content=context.position_content(animated_content), backdrop=backdrop)


__all__ = ["OverlayVisualState", "MaterialOverlayVisualMapper", "MaterialOverlayLayerComposer"]
