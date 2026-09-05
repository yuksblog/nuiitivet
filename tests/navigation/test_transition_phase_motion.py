"""Tests for phase → motion resolution shared by navigator and overlay."""

from __future__ import annotations

from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern
from nuiitivet.animation.motion import BezierMotion
from nuiitivet.material.transition_spec import MaterialTransitionSpec, MaterialTransitions
from nuiitivet.navigation.transition_spec import TransitionPhase, resolve_phase_motion


def _definition(duration: float) -> TransitionDefinition:
    return TransitionDefinition(motion=BezierMotion(0, 0, 1, 1, duration), pattern=FadePattern())


def test_exit_motion_resolves_despite_trailing_underscore_field() -> None:
    """The exit definition lives under ``exit_``; resolution must not miss it
    and silently fall back to the engine default motion."""
    spec = MaterialTransitions.dialog()

    enter = resolve_phase_motion(spec, TransitionPhase.ENTER)
    exit_ = resolve_phase_motion(spec, TransitionPhase.EXIT)

    assert enter is spec.enter.motion
    assert exit_ is spec.exit_.motion


def test_back_variant_motion_preferred_on_back_navigation() -> None:
    spec = MaterialTransitionSpec(
        enter=_definition(0.1),
        exit_=_definition(0.2),
        enter_back=_definition(0.3),
        exit_back=_definition(0.4),
    )

    assert spec.enter_back is not None and spec.exit_back is not None
    assert resolve_phase_motion(spec, TransitionPhase.ENTER, back=True) is spec.enter_back.motion
    assert resolve_phase_motion(spec, TransitionPhase.EXIT, back=True) is spec.exit_back.motion
    # Forward navigation ignores the back variants.
    assert resolve_phase_motion(spec, TransitionPhase.ENTER) is spec.enter.motion
    assert resolve_phase_motion(spec, TransitionPhase.EXIT) is spec.exit_.motion


def test_back_variant_falls_back_to_forward_definition() -> None:
    spec = MaterialTransitionSpec(enter=_definition(0.1), exit_=_definition(0.2))

    assert resolve_phase_motion(spec, TransitionPhase.ENTER, back=True) is spec.enter.motion
    assert resolve_phase_motion(spec, TransitionPhase.EXIT, back=True) is spec.exit_.motion


def test_active_phase_has_no_motion() -> None:
    spec = MaterialTransitions.dialog()

    assert resolve_phase_motion(spec, TransitionPhase.ACTIVE) is None
