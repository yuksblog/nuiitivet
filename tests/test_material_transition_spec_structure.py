"""Test structure and defaults of Material transition specs."""

from nuiitivet.material.transition_spec import (
    MaterialDialogTransitionSpec,
    MaterialPageTransitionSpec,
    MaterialTransitions,
)
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import (
    FadePattern,
    ScalePattern,
    CompositePattern,
)
from nuiitivet.animation.motion import BezierMotion
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS


def test_dialog_spec_defaults():
    spec = MaterialTransitions.dialog()

    assert isinstance(spec, MaterialDialogTransitionSpec)
    assert isinstance(spec.enter, TransitionDefinition)
    assert isinstance(spec.exit, TransitionDefinition)

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

    spec = MaterialTransitions.dialog(enter=custom_enter, exit=custom_exit)

    assert spec.enter is custom_enter
    assert spec.exit is custom_exit


def test_page_spec_defaults():
    spec = MaterialTransitions.page()

    assert isinstance(spec, MaterialPageTransitionSpec)

    # Page Default Enter is just Fade
    # Wait, check implementation: Is it FadePattern or Composite?
    # _default_page_enter uses just FadePattern.
    assert isinstance(spec.enter.pattern, FadePattern)

    assert spec.enter.pattern.start_alpha == 0.0
    assert spec.enter.pattern.end_alpha == 1.0


def test_page_spec_custom():
    custom = TransitionDefinition(
        motion=BezierMotion(0, 0, 0, 0, 0),
        pattern=FadePattern(),
    )
    spec = MaterialTransitions.page(enter=custom)

    assert spec.enter is custom
    # Exit should be default
    assert isinstance(spec.exit.pattern, FadePattern)
    assert spec.exit.pattern.start_alpha == 1.0
