"""Material transition visual parameter resolution."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.navigation.transition_spec import (
    EmptyTransitionSpec,
    TransitionPhase,
    TransitionSpec,
)

from .transition_spec import (
    MaterialDialogTransitionSpec,
    MaterialPageTransitionSpec,
    MaterialSnackbarTransitionSpec,
)


@dataclass(frozen=True, slots=True)
class MaterialTransitionVisualSpec:
    """Resolved Material visual parameters for one transition tick."""

    content_opacity: float
    content_scale: tuple[float, float]
    content_translation: tuple[float, float]
    barrier_opacity: float | None


def resolve_material_transition_visual_spec(
    transition_spec: TransitionSpec,
    *,
    phase: TransitionPhase,
    progress: float,
) -> MaterialTransitionVisualSpec:
    """Resolve material visual parameters from a lifecycle transition token."""
    p = _clamp01(progress)

    if isinstance(transition_spec, EmptyTransitionSpec):
        return MaterialTransitionVisualSpec(
            content_opacity=1.0,
            content_scale=(1.0, 1.0),
            content_translation=(0.0, 0.0),
            barrier_opacity=None,
        )

    # Common logic for Material specs that use TransitionDefinition
    definition = None
    barrier: float | None = None

    if isinstance(transition_spec, MaterialPageTransitionSpec):
        if phase is TransitionPhase.ENTER:
            definition = transition_spec.enter
        elif phase is TransitionPhase.EXIT:
            definition = transition_spec.exit
        # Page transitions don't have a barrier
        barrier = None

    elif isinstance(transition_spec, MaterialDialogTransitionSpec):
        if phase is TransitionPhase.ENTER:
            definition = transition_spec.enter
            barrier = p  # Default linear fade for barrier
        elif phase is TransitionPhase.EXIT:
            definition = transition_spec.exit
            barrier = 1.0 - p
        else:
            barrier = 1.0

    elif isinstance(transition_spec, MaterialSnackbarTransitionSpec):
        if phase is TransitionPhase.ENTER:
            definition = transition_spec.enter
        elif phase is TransitionPhase.EXIT:
            definition = transition_spec.exit
        # Snakebars don't have a barrier (or pass-through)
        barrier = None

    if definition is not None:
        visuals = definition.pattern.resolve(p)

        opacity = visuals.opacity if visuals.opacity is not None else 1.0
        scale_x = visuals.scale_x if visuals.scale_x is not None else 1.0
        scale_y = visuals.scale_y if visuals.scale_y is not None else 1.0
        trans_x = visuals.translate_x if visuals.translate_x is not None else 0.0
        trans_y = visuals.translate_y if visuals.translate_y is not None else 0.0

        return MaterialTransitionVisualSpec(
            content_opacity=opacity,
            content_scale=(scale_x, scale_y),
            content_translation=(trans_x, trans_y),
            barrier_opacity=barrier,
        )

    # Fallback / Active state
    return MaterialTransitionVisualSpec(
        content_opacity=1.0,
        content_scale=(1.0, 1.0),
        content_translation=(0.0, 0.0),
        barrier_opacity=barrier,
    )


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _lerp(start: float, end: float, t: float) -> float:
    return float(start) + (float(end) - float(start)) * _clamp01(t)


__all__ = ["MaterialTransitionVisualSpec", "resolve_material_transition_visual_spec"]
