"""Transition definition combining motion and pattern.

A TransitionDefinition holds both the timing (Motion) and the visual effect (Pattern).
"""

from __future__ import annotations

from dataclasses import dataclass

from .motion import Motion
from .transition_pattern import TransitionPattern, CompositePattern


@dataclass(frozen=True)
class TransitionDefinition:
    """Defines a complete transition with motion and pattern."""

    motion: Motion
    pattern: TransitionPattern

    def __or__(self, other: TransitionDefinition) -> TransitionDefinition:
        """Combine two definitions.

        The resulting definition uses the motion from this (left-hand) definition
        and combines the patterns of both.
        """
        # Note: We prioritize the motion of the left operand.
        # This allows:
        #   FadeIn(long_duration) | SlideIn(short_default)
        # to result in a transition running for `long_duration`.
        # The patterns are composed so both effects apply.
        return TransitionDefinition(
            motion=self.motion,
            pattern=CompositePattern(self.pattern, other.pattern),
        )
