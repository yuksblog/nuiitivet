"""Tests for the MD3 Shared Axis (X) default page transition.

See issue #402. The default ``MaterialTransitions.page()`` transition follows the
Material Components for Android Shared Axis (X) pattern:

- a subtle horizontal slide plus a "fade through" (the outgoing page fades out
  early, the incoming page fades in late) rather than a plain simultaneous fade;
- push (forward) enters from the right / exits to the left, and pop (backward)
  reverses that direction.
"""

from __future__ import annotations

from nuiitivet.material.transition_spec import MaterialTransitions
from nuiitivet.material.transition_visual_spec import resolve_material_transition_visual_spec
from nuiitivet.navigation.layer_composer import NavigationTransitionKind
from nuiitivet.navigation.transition_spec import TransitionPhase


def _translate_x(spec, *, phase: TransitionPhase, progress: float, kind: NavigationTransitionKind) -> float:
    visual = resolve_material_transition_visual_spec(spec, phase=phase, progress=progress, kind=kind)
    return visual.content_translation[0]


def _opacity(spec, *, phase: TransitionPhase, progress: float, kind: NavigationTransitionKind) -> float:
    visual = resolve_material_transition_visual_spec(spec, phase=phase, progress=progress, kind=kind)
    return visual.content_opacity


def test_page_default_slides_horizontally_not_plain_fade() -> None:
    """The default page transition carries a horizontal slide (Shared Axis X)."""
    spec = MaterialTransitions.page()
    start = _translate_x(spec, phase=TransitionPhase.ENTER, progress=0.0, kind="push")
    assert start != 0.0, "default page transition must carry a horizontal slide, not fade only"


def test_push_incoming_enters_from_right() -> None:
    """Forward push: incoming page slides from the right (+x) to rest (0)."""
    spec = MaterialTransitions.page()
    start = _translate_x(spec, phase=TransitionPhase.ENTER, progress=0.0, kind="push")
    end = _translate_x(spec, phase=TransitionPhase.ENTER, progress=1.0, kind="push")
    assert start > 0.0
    assert end == 0.0


def test_push_outgoing_exits_to_left() -> None:
    """Forward push: outgoing page slides from rest (0) to the left (-x)."""
    spec = MaterialTransitions.page()
    start = _translate_x(spec, phase=TransitionPhase.EXIT, progress=0.0, kind="push")
    end = _translate_x(spec, phase=TransitionPhase.EXIT, progress=1.0, kind="push")
    assert start == 0.0
    assert end < 0.0


def test_pop_reverses_slide_direction() -> None:
    """Backward pop mirrors the push slide direction on both pages."""
    spec = MaterialTransitions.page()

    # Returning page (ENTER): push comes from the right, pop comes from the left.
    push_enter = _translate_x(spec, phase=TransitionPhase.ENTER, progress=0.0, kind="push")
    pop_enter = _translate_x(spec, phase=TransitionPhase.ENTER, progress=0.0, kind="pop")
    assert push_enter > 0.0 > pop_enter

    # Leaving page (EXIT): push exits left, pop exits right.
    push_exit = _translate_x(spec, phase=TransitionPhase.EXIT, progress=1.0, kind="push")
    pop_exit = _translate_x(spec, phase=TransitionPhase.EXIT, progress=1.0, kind="pop")
    assert push_exit < 0.0 < pop_exit


def test_fade_through_incoming_holds_transparent_early() -> None:
    """Incoming page stays transparent until the fade-through threshold, then fades in."""
    spec = MaterialTransitions.page()
    assert _opacity(spec, phase=TransitionPhase.ENTER, progress=0.2, kind="push") == 0.0
    assert _opacity(spec, phase=TransitionPhase.ENTER, progress=1.0, kind="push") == 1.0


def test_fade_through_outgoing_gone_by_threshold() -> None:
    """Outgoing page finishes fading out early, so pages never both sit half-opaque."""
    spec = MaterialTransitions.page()
    assert _opacity(spec, phase=TransitionPhase.EXIT, progress=0.35, kind="push") == 0.0
    # Held transparent afterwards.
    assert _opacity(spec, phase=TransitionPhase.EXIT, progress=0.5, kind="push") == 0.0


def test_no_muddy_midpoint() -> None:
    """At the midpoint the two pages must not both be substantially opaque."""
    spec = MaterialTransitions.page()
    incoming = _opacity(spec, phase=TransitionPhase.ENTER, progress=0.5, kind="push")
    outgoing = _opacity(spec, phase=TransitionPhase.EXIT, progress=0.5, kind="push")
    # The outgoing page is already gone; only the incoming is partially visible.
    assert outgoing == 0.0
    assert incoming < 0.5


def test_dialog_is_symmetric_direction_agnostic() -> None:
    """Symmetric transitions (dialog) have no back variant: pop mirrors push."""
    spec = MaterialTransitions.dialog()
    assert spec.enter_back is None
    assert spec.exit_back is None
    push_enter = _opacity(spec, phase=TransitionPhase.ENTER, progress=0.5, kind="push")
    pop_enter = _opacity(spec, phase=TransitionPhase.ENTER, progress=0.5, kind="pop")
    assert push_enter == pop_enter


def test_custom_enter_override_mirrors_to_pop_by_default() -> None:
    """A custom forward ``enter`` with no ``enter_back`` is mirrored for pop."""
    from nuiitivet.animation.transition_definition import TransitionDefinition
    from nuiitivet.animation.transition_pattern import FadePattern
    from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS

    custom_enter = TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=0.0, end_alpha=1.0),
    )
    spec = MaterialTransitions.page(enter=custom_enter)
    assert spec.enter_back is custom_enter
    push_enter = _translate_x(spec, phase=TransitionPhase.ENTER, progress=0.0, kind="push")
    pop_enter = _translate_x(spec, phase=TransitionPhase.ENTER, progress=0.0, kind="pop")
    assert push_enter == pop_enter == 0.0
