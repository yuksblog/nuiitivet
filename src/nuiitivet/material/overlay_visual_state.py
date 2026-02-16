"""Material-specific overlay visual mapping and composition."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.modifiers import opacity, scale, translate
from nuiitivet.modifiers.background import background
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.navigation.transition_state import TransitionLifecycle
from nuiitivet.observable import combine
from nuiitivet.overlay.layer_composer import OverlayLayerComposer, OverlayLayerCompositionContext
from nuiitivet.widgeting.widget import Widget

from .transition_visual_spec import resolve_material_transition_visual_spec


@dataclass(frozen=True, slots=True)
class OverlayVisualState:
    """Material visual parameters for one overlay transition frame."""

    content_opacity: float
    content_scale: tuple[float, float]
    content_translation: tuple[float, float]
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
            barrier_opacity=visual.barrier_opacity,
        )


class MaterialOverlayLayerComposer(OverlayLayerComposer):
    """Material implementation of overlay layer composition."""

    def __init__(self, mapper: MaterialOverlayVisualMapper | None = None) -> None:
        self._mapper = mapper or MaterialOverlayVisualMapper()

    def compose(self, context: OverlayLayerCompositionContext) -> Widget:
        lifecycle_obs = context.transition_state.lifecycle_obs
        visual_obs = combine(lifecycle_obs).compute(lambda lifecycle: self._mapper.map_lifecycle(context, lifecycle))

        content_opacity_obs = combine(visual_obs).compute(lambda state: state.content_opacity)
        content_scale_obs = combine(visual_obs).compute(lambda state: state.content_scale)
        content_translation_obs = combine(visual_obs).compute(lambda state: state.content_translation)
        barrier_opacity_obs = combine(visual_obs).compute(
            lambda state: 1.0 if state.barrier_opacity is None else state.barrier_opacity
        )

        animated_content = context.content.modifier(
            opacity(content_opacity_obs) | scale(content_scale_obs) | translate(content_translation_obs)
        )
        positioned_content = context.position_content(animated_content)

        if context.passthrough:
            return positioned_content

        barrier = Container(width="100%", height="100%").modifier(
            background(context.barrier_color)
            | opacity(barrier_opacity_obs)
            | clickable(on_click=context.on_barrier_click if context.barrier_dismissible else None)
        )
        return Stack(children=[barrier, positioned_content], alignment="top-left", width="100%", height="100%")


__all__ = ["OverlayVisualState", "MaterialOverlayVisualMapper", "MaterialOverlayLayerComposer"]
