"""Material motion tokens for declarative animation.

Defines motion specs based on M3 Expressive web-converted curves.
Durations are in seconds.
"""

from __future__ import annotations

import math

from nuiitivet.animation.motion import BezierMotion, Motion, SpringMotion


# Expressive spatial
EXPRESSIVE_FAST_SPATIAL: Motion = BezierMotion(0.42, 1.67, 0.21, 0.90, 0.35)
EXPRESSIVE_DEFAULT_SPATIAL: Motion = BezierMotion(0.38, 1.21, 0.22, 1.00, 0.50)
EXPRESSIVE_SLOW_SPATIAL: Motion = BezierMotion(0.39, 1.29, 0.35, 0.98, 0.65)

# Expressive effects
EXPRESSIVE_FAST_EFFECTS: Motion = BezierMotion(0.31, 0.94, 0.34, 1.00, 0.15)
EXPRESSIVE_DEFAULT_EFFECTS: Motion = BezierMotion(0.34, 0.80, 0.34, 1.00, 0.20)
EXPRESSIVE_SLOW_EFFECTS: Motion = BezierMotion(0.34, 0.88, 0.34, 1.00, 0.30)

# Standard button group — pressed item width spring.
# MD3 token: dampening (ratio) 0.9, stiffness 1400 (all sizes).  The damping
# coefficient is derived from the ratio with unit mass: c = 2 * ζ * sqrt(k * m).
_BTN_GROUP_WIDTH_STIFFNESS = 1400.0
_BTN_GROUP_WIDTH_DAMPING_RATIO = 0.9
STANDARD_BUTTON_GROUP_WIDTH: Motion = SpringMotion(
    stiffness=_BTN_GROUP_WIDTH_STIFFNESS,
    damping=2.0 * _BTN_GROUP_WIDTH_DAMPING_RATIO * math.sqrt(_BTN_GROUP_WIDTH_STIFFNESS),
    mass=1.0,
)


__all__ = [
    "EXPRESSIVE_FAST_SPATIAL",
    "EXPRESSIVE_DEFAULT_SPATIAL",
    "EXPRESSIVE_SLOW_SPATIAL",
    "EXPRESSIVE_FAST_EFFECTS",
    "EXPRESSIVE_DEFAULT_EFFECTS",
    "EXPRESSIVE_SLOW_EFFECTS",
    "STANDARD_BUTTON_GROUP_WIDTH",
]
