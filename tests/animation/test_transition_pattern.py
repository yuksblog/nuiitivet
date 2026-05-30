"""Test transition pattern composition and resolution."""

from nuiitivet.animation.transition_pattern import (
    FadePattern,
    ScalePattern,
    SlidePattern,
    CompositePattern,
)
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.motion import LinearMotion


def test_fade_pattern_resolve():
    pattern = FadePattern(start_alpha=0.2, end_alpha=0.8)

    vis_start = pattern.resolve(0.0)
    assert vis_start.opacity == 0.2

    vis_mid = pattern.resolve(0.5)
    assert abs(vis_mid.opacity - 0.5) < 1e-6

    vis_end = pattern.resolve(1.0)
    assert vis_end.opacity == 0.8


def test_slide_pattern_resolve():
    pattern = SlidePattern(start_x=10, start_y=20, end_x=30, end_y=40)

    vis_start = pattern.resolve(0.0)
    assert vis_start.translate_x == 10
    assert vis_start.translate_y == 20

    vis_mid = pattern.resolve(0.5)
    assert vis_mid.translate_x == 20
    assert vis_mid.translate_y == 30


def test_composite_pattern_resolve():
    # Combine Fade (alpha) and Scale
    fade = FadePattern(start_alpha=0.0, end_alpha=1.0)
    scale = ScalePattern(start_scale_x=0.5, start_scale_y=0.5, end_scale_x=1.0, end_scale_y=1.0)

    composite = fade | scale

    vis_mid = composite.resolve(0.5)
    assert vis_mid.opacity == 0.5
    assert vis_mid.scale_x == 0.75
    assert vis_mid.scale_y == 0.75


def test_composite_pattern_merge_order():
    # Verify that later patterns overwrite earlier ones if they touch the same property,
    # or just combine them.
    # In our implementation `TransitionVisuals.merge` prioritizes `other` (the second one) if not None.

    p1 = SlidePattern(start_x=0, end_x=100)  # sets translate_x, translate_y
    p2 = SlidePattern(start_x=50, end_x=150)  # sets translate_x, translate_y

    composite = p1 | p2

    # At progress 0.0: p1 gives 0, p2 gives 50. p2 should win.
    vis = composite.resolve(0.0)
    assert vis.translate_x == 50


def test_transition_definition_composition():
    motion1 = LinearMotion(duration=1.0)
    motion2 = LinearMotion(duration=0.5)  # Should be ignored

    def1 = TransitionDefinition(motion=motion1, pattern=FadePattern())
    def2 = TransitionDefinition(motion=motion2, pattern=ScalePattern())

    # def1 is left, so motion1 should be used
    composite_def = def1 | def2

    assert composite_def.motion is motion1
    assert isinstance(composite_def.pattern, CompositePattern)

    vis = composite_def.pattern.resolve(0.5)
    # Default fade: 0 -> 1 => 0.5
    # Default scale: 0.8 -> 1 => 0.9
    assert vis.opacity == 0.5
    assert vis.scale_x == 0.9
