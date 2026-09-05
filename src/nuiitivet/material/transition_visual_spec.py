"""Material transition visual parameter resolution."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.navigation.layer_composer import NavigationTransitionKind
from nuiitivet.navigation.transition_spec import (
    EmptyTransitionSpec,
    TransitionPhase,
    TransitionSpec,
)

from .transition_spec import MaterialTransitionSpec


@dataclass(frozen=True, slots=True)
class MaterialTransitionVisualSpec:
    """Resolved Material visual parameters for one transition tick."""

    content_opacity: float
    content_scale: tuple[float, float]
    content_translation: tuple[float, float]
    content_translation_fraction: tuple[float, float]
    barrier_opacity: float | None


def resolve_material_transition_visual_spec(
    transition_spec: TransitionSpec,
    *,
    phase: TransitionPhase,
    progress: float,
    kind: NavigationTransitionKind | None = None,
) -> MaterialTransitionVisualSpec:
    """Resolve material visual parameters from a lifecycle transition token.

    Args:
        transition_spec: The lifecycle token to resolve.
        phase: Whether the widget is entering or exiting this frame.
        progress: Normalized progress in ``[0.0, 1.0]``.
        kind: Navigation direction. On ``"pop"`` the backward-direction
            definitions (``enter_back`` / ``exit_back``) are used when present,
            so directional patterns such as Shared Axis (Z) reverse correctly
            instead of replaying the forward motion.

    Progress above ``1.0`` is passed through to the patterns rather than
    clamped: expressive spatial curves overshoot their target and settle, and
    slide/scale patterns extrapolate linearly to render that settle. Fades
    clamp themselves, and the scrim is clamped here, so only spatial
    properties overshoot.
    """
    p = max(0.0, float(progress))

    if isinstance(transition_spec, EmptyTransitionSpec):
        return MaterialTransitionVisualSpec(
            content_opacity=1.0,
            content_scale=(1.0, 1.0),
            content_translation=(0.0, 0.0),
            content_translation_fraction=(0.0, 0.0),
            barrier_opacity=None,
        )

    if not isinstance(transition_spec, MaterialTransitionSpec):
        # Unknown spec kind: pass-through active state.
        return MaterialTransitionVisualSpec(
            content_opacity=1.0,
            content_scale=(1.0, 1.0),
            content_translation=(0.0, 0.0),
            content_translation_fraction=(0.0, 0.0),
            barrier_opacity=None,
        )

    # Resolve enter/exit definition. On a backward navigation (pop) prefer the
    # direction-specific variant so reversible patterns (Shared Axis X) play in
    # reverse; fall back to the forward definition when no back variant is set
    # (symmetric transitions: dialog, sheets, snackbar).
    is_back = kind == "pop"
    if phase is TransitionPhase.ENTER:
        back = transition_spec.enter_back
        definition = back if is_back and back is not None else transition_spec.enter
    elif phase is TransitionPhase.EXIT:
        back = transition_spec.exit_back
        definition = back if is_back and back is not None else transition_spec.exit_
    else:
        definition = None

    # Resolve barrier opacity from barrier_mode
    barrier: float | None
    if transition_spec.barrier_mode == "fade":
        if phase is TransitionPhase.ENTER:
            barrier = _clamp01(p)
        elif phase is TransitionPhase.EXIT:
            barrier = _clamp01(1.0 - p)
        else:
            barrier = 1.0
    else:  # "none"
        barrier = None

    if definition is not None:
        visuals = definition.pattern.resolve(p)

        opacity = visuals.opacity if visuals.opacity is not None else 1.0
        scale_x = visuals.scale_x if visuals.scale_x is not None else 1.0
        scale_y = visuals.scale_y if visuals.scale_y is not None else 1.0
        trans_x = visuals.translate_x if visuals.translate_x is not None else 0.0
        trans_y = visuals.translate_y if visuals.translate_y is not None else 0.0
        trans_fx = visuals.translate_x_fraction if visuals.translate_x_fraction is not None else 0.0
        trans_fy = visuals.translate_y_fraction if visuals.translate_y_fraction is not None else 0.0

        return MaterialTransitionVisualSpec(
            content_opacity=opacity,
            content_scale=(scale_x, scale_y),
            content_translation=(trans_x, trans_y),
            content_translation_fraction=(trans_fx, trans_fy),
            barrier_opacity=barrier,
        )

    # Fallback / Active state
    return MaterialTransitionVisualSpec(
        content_opacity=1.0,
        content_scale=(1.0, 1.0),
        content_translation=(0.0, 0.0),
        content_translation_fraction=(0.0, 0.0),
        barrier_opacity=barrier,
    )


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _lerp(start: float, end: float, t: float) -> float:
    return float(start) + (float(end) - float(start)) * _clamp01(t)


__all__ = ["MaterialTransitionVisualSpec", "resolve_material_transition_visual_spec"]
