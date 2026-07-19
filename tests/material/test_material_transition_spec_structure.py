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
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS


def test_dialog_spec_defaults():
    spec = MaterialTransitions.dialog()

    assert isinstance(spec, MaterialTransitionSpec)
    assert spec.barrier_mode == "fade"
    assert isinstance(spec.enter, TransitionDefinition)
    assert isinstance(spec.exit_, TransitionDefinition)

    # Check default Dialog Enter: Fade | Scale
    assert isinstance(spec.enter.pattern, CompositePattern)
    # Checking implementation details of defaults slightly, but necessary for verification
    # Note: CompositePattern structure depends on order (Fade | Scale)

    # Default motion
    assert isinstance(spec.enter.motion, BezierMotion)
    assert spec.enter.motion.duration == EXPRESSIVE_DEFAULT_EFFECTS.duration


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
