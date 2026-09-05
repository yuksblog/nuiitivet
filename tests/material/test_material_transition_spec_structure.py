"""Test structure and defaults of Material transition specs."""

from nuiitivet.material.transition_spec import (
    MaterialTransitionSpec,
    MaterialTransitions,
)
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import (
    FadePattern,
    ScalePattern,
    SlidePattern,
    CompositePattern,
)
from nuiitivet.animation.motion import BezierMotion
from nuiitivet.material.motion import (
    EXPRESSIVE_DEFAULT_SPATIAL,
    EXPRESSIVE_FAST_EFFECTS,
    EXPRESSIVE_FAST_SPATIAL,
)


def test_dialog_spec_defaults():
    spec = MaterialTransitions.dialog()

    assert isinstance(spec, MaterialTransitionSpec)
    assert spec.barrier_mode == "fade"
    assert isinstance(spec.enter, TransitionDefinition)
    assert isinstance(spec.exit_, TransitionDefinition)

    # Enter: Fade | Scale on spatial timing (scale is the spatial motion).
    assert isinstance(spec.enter.pattern, CompositePattern)
    assert isinstance(spec.enter.motion, BezierMotion)
    assert spec.enter.motion is EXPRESSIVE_DEFAULT_SPATIAL

    # Exit: plain fade-out over a shorter run (effects: the fade is the motion).
    assert isinstance(spec.exit_.pattern, FadePattern)
    assert spec.exit_.motion is EXPRESSIVE_FAST_EFFECTS
    assert spec.exit_.motion.duration < spec.enter.motion.duration


def test_snackbar_spec_enter_exit_asymmetry():
    spec = MaterialTransitions.snackbar()

    assert spec.enter.motion is EXPRESSIVE_FAST_SPATIAL
    assert spec.exit_.motion is EXPRESSIVE_FAST_EFFECTS
    assert spec.exit_.motion.duration < spec.enter.motion.duration
    # Exit drops the slide and only fades.
    assert isinstance(spec.exit_.pattern, FadePattern)


def test_sheet_specs_enter_exit_asymmetry():
    for spec in (MaterialTransitions.side_sheet(), MaterialTransitions.bottom_sheet()):
        assert spec.barrier_mode == "fade"
        assert spec.enter.motion is EXPRESSIVE_DEFAULT_SPATIAL
        # The slide-out stays spatial; the fast speed keeps it shorter.
        assert spec.exit_.motion is EXPRESSIVE_FAST_SPATIAL
        assert spec.exit_.motion.duration < spec.enter.motion.duration


def test_dialog_spec_custom():
    custom_enter = TransitionDefinition(
        motion=BezierMotion(0, 0, 1, 1, duration=1.0),
        pattern=FadePattern(start_alpha=0.5),
    )
    custom_exit = TransitionDefinition(
        motion=BezierMotion(0, 0, 1, 1, duration=0.5),
        pattern=ScalePattern(start_scale_x=0.5),
    )

    spec = MaterialTransitions.dialog(enter=custom_enter, exit_=custom_exit)

    assert spec.enter is custom_enter
    assert spec.exit_ is custom_exit


def test_page_spec_defaults():
    spec = MaterialTransitions.page()

    assert isinstance(spec, MaterialTransitionSpec)
    assert spec.barrier_mode == "none"

    # Page default is MD3 Shared Axis (X): a fade-through composed with a subtle
    # horizontal slide, not a plain fade. The composite carries the Fade first.
    assert isinstance(spec.enter.pattern, CompositePattern)
    assert isinstance(spec.enter.pattern.first, FadePattern)
    assert isinstance(spec.enter.pattern.second, SlidePattern)
    # Fade-through: incoming fades in over the later part of the transition.
    assert spec.enter.pattern.first.start_alpha == 0.0
    assert spec.enter.pattern.first.end_alpha == 1.0
    assert spec.enter.pattern.first.start_progress > 0.0
    # Incoming slides in from the right (positive x) toward rest (0).
    assert spec.enter.pattern.second.start_x > 0.0
    assert spec.enter.pattern.second.end_x == 0.0

    # Direction-aware: backward (pop) variants are populated for the default.
    assert isinstance(spec.enter_back, TransitionDefinition)
    assert isinstance(spec.exit_back, TransitionDefinition)


def test_page_spec_custom():
    custom = TransitionDefinition(
        motion=BezierMotion(0, 0, 0, 0, 0),
        pattern=FadePattern(),
    )
    spec = MaterialTransitions.page(enter=custom)

    assert spec.enter is custom
    # Exit should be the default Shared Axis Z outgoing (Fade | Scale).
    assert isinstance(spec.exit_.pattern, CompositePattern)
    assert isinstance(spec.exit_.pattern.first, FadePattern)
    assert spec.exit_.pattern.first.start_alpha == 1.0
    # A custom forward enter with no enter_back is mirrored onto pop.
    assert spec.enter_back is custom
