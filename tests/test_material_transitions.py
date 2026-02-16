"""Test public Material transition presets."""

from nuiitivet.material.transitions import (
    FadeIn,
    FadeOut,
    ScaleIn,
    ScaleOut,
    SlideInVertically,
)
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import (
    FadePattern,
    ScalePattern,
    SlidePattern,
)
from nuiitivet.animation.motion import BezierMotion


def test_fade_in_factory():
    t = FadeIn(alpha=0.2, duration=1.5)

    assert isinstance(t, TransitionDefinition)
    assert isinstance(t.motion, BezierMotion)
    assert t.motion.duration == 1.5

    assert isinstance(t.pattern, FadePattern)
    assert t.pattern.start_alpha == 0.2
    assert t.pattern.end_alpha == 1.0


def test_fade_out_factory():
    t = FadeOut(alpha=0.5, duration=0.5)

    assert isinstance(t, TransitionDefinition)
    assert isinstance(t.pattern, FadePattern)
    assert t.pattern.start_alpha == 1.0
    assert t.pattern.end_alpha == 0.5


def test_scale_in_factory():
    t = ScaleIn(initial_scale=0.5)

    assert isinstance(t, TransitionDefinition)
    assert isinstance(t.pattern, ScalePattern)
    assert t.pattern.start_scale_x == 0.5
    assert t.pattern.end_scale_x == 1.0


def test_scale_out_factory():
    t = ScaleOut(target_scale=0.1)

    assert isinstance(t, TransitionDefinition)
    assert isinstance(t.pattern, ScalePattern)
    assert t.pattern.start_scale_x == 1.0
    assert t.pattern.end_scale_x == 0.1


def test_slide_in_vertically_factory():
    t = SlideInVertically(initial_offset_y=100)

    assert isinstance(t, TransitionDefinition)
    assert isinstance(t.pattern, SlidePattern)
    assert t.pattern.start_y == 100
    assert t.pattern.end_y == 0.0


def test_composition_preset():
    # Verify we can use the | operator on presets
    complex_t = FadeIn() | ScaleIn()

    assert isinstance(complex_t, TransitionDefinition)
    # Composition logic creates composite pattern
    # It might be CompositePattern(FadePattern, ScalePattern) if implemented that way

    vis = complex_t.pattern.resolve(0.0)
    # FadeIn default starts at 0.0
    # ScaleIn default starts at 0.9
    assert vis.opacity == 0.0
    assert vis.scale_x == 0.9
