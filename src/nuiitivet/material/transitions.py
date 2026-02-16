"""Material transition presets and factories.

Provides explicit entry points for creating transition effects.
Users should prefer this module over constructing raw definitions.

Example:
    MaterialTransitions.dialog(
        enter=FadeIn() | ScaleIn(),
        exit=FadeOut(duration=0.2),
    )
"""

from __future__ import annotations

from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import (
    FadePattern,
    ScalePattern,
    SlidePattern,
)
from nuiitivet.animation.motion import BezierMotion, Motion

# Standard durations from Material Design 3 guidelines
_DURATION_SHORT_1 = 0.05
_DURATION_SHORT_2 = 0.1
_DURATION_SHORT_3 = 0.15
_DURATION_SHORT_4 = 0.2
_DURATION_MEDIUM_1 = 0.25
_DURATION_MEDIUM_2 = 0.3
_DURATION_MEDIUM_3 = 0.35
_DURATION_MEDIUM_4 = 0.4
_DURATION_LONG_1 = 0.45
_DURATION_LONG_2 = 0.5
_DURATION_LONG_3 = 0.55
_DURATION_LONG_4 = 0.6


def _standard_motion(duration: float) -> Motion:
    """Standard ease-out motion (Emphasized Decelerate approximation)."""
    return BezierMotion(0.0, 0.0, 0.2, 1.0, duration=duration)


def FadeIn(
    *,
    alpha: float = 0.0,
    duration: float = _DURATION_MEDIUM_2,  # 0.3s
) -> TransitionDefinition:
    """Fade in from a specific alpha to 1.0."""
    return TransitionDefinition(
        motion=_standard_motion(duration),
        pattern=FadePattern(start_alpha=alpha, end_alpha=1.0),
    )


def FadeOut(
    *,
    alpha: float = 0.0,
    duration: float = _DURATION_SHORT_4,  # 0.2s
) -> TransitionDefinition:
    """Fade out from 1.0 to a specific alpha."""
    return TransitionDefinition(
        motion=_standard_motion(duration),
        pattern=FadePattern(start_alpha=1.0, end_alpha=alpha),
    )


def ScaleIn(
    *,
    initial_scale: float = 0.9,
    duration: float = _DURATION_MEDIUM_2,
) -> TransitionDefinition:
    """Scale up from initial_scale to 1.0."""
    return TransitionDefinition(
        motion=_standard_motion(duration),
        pattern=ScalePattern(
            start_scale_x=initial_scale,
            start_scale_y=initial_scale,
            end_scale_x=1.0,
            end_scale_y=1.0,
        ),
    )


def ScaleOut(
    *,
    target_scale: float = 0.9,
    duration: float = _DURATION_SHORT_4,
) -> TransitionDefinition:
    """Scale down from 1.0 to target_scale."""
    return TransitionDefinition(
        motion=_standard_motion(duration),
        pattern=ScalePattern(
            start_scale_x=1.0,
            start_scale_y=1.0,
            end_scale_x=target_scale,
            end_scale_y=target_scale,
        ),
    )


def SlideInVertically(
    *,
    initial_offset_y: float = 20.0,
    duration: float = _DURATION_MEDIUM_2,
) -> TransitionDefinition:
    """Slide in vertically from an offset to 0."""
    return TransitionDefinition(
        motion=_standard_motion(duration),
        pattern=SlidePattern(start_y=initial_offset_y, end_y=0.0),
    )


def SlideOutVertically(
    *,
    target_offset_y: float = 20.0,
    duration: float = _DURATION_SHORT_4,
) -> TransitionDefinition:
    """Slide out vertically from 0 to target offset."""
    return TransitionDefinition(
        motion=_standard_motion(duration),
        pattern=SlidePattern(start_y=0.0, end_y=target_offset_y),
    )


__all__ = [
    "FadeIn",
    "FadeOut",
    "ScaleIn",
    "ScaleOut",
    "SlideInVertically",
    "SlideOutVertically",
]
