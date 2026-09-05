"""Material motion tokens for declarative animation.

Carries the MD3 motion-scheme table (expressive and standard schemes, spatial
and effects rows) as web-converted bezier curves. Durations are in seconds.
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

# Standard spatial — one curve for all three speeds; only the duration varies.
STANDARD_FAST_SPATIAL: Motion = BezierMotion(0.27, 1.06, 0.18, 1.00, 0.35)
STANDARD_DEFAULT_SPATIAL: Motion = BezierMotion(0.27, 1.06, 0.18, 1.00, 0.50)
STANDARD_SLOW_SPATIAL: Motion = BezierMotion(0.27, 1.06, 0.18, 1.00, 0.75)

# Standard effects — the two schemes share their effects rows verbatim.
STANDARD_FAST_EFFECTS: Motion = EXPRESSIVE_FAST_EFFECTS
STANDARD_DEFAULT_EFFECTS: Motion = EXPRESSIVE_DEFAULT_EFFECTS
STANDARD_SLOW_EFFECTS: Motion = EXPRESSIVE_SLOW_EFFECTS

# Standard fast spatial as a spring — the same token as STANDARD_FAST_SPATIAL
# in its native md.sys.motion.spring form (damping ratio 0.9, stiffness 1400;
# the coefficient derives from the ratio with unit mass: c = 2 * ζ * sqrt(k * m)).
# Prefer the spring over the bezier where an animation retargets mid-flight and
# must carry its velocity into the new target.
_STD_FAST_SPATIAL_STIFFNESS = 1400.0
_STD_FAST_SPATIAL_DAMPING_RATIO = 0.9
SPRING_STANDARD_FAST_SPATIAL: Motion = SpringMotion(
    stiffness=_STD_FAST_SPATIAL_STIFFNESS,
    damping=2.0 * _STD_FAST_SPATIAL_DAMPING_RATIO * math.sqrt(_STD_FAST_SPATIAL_STIFFNESS),
    mass=1.0,
)

# Standard button group — pressed item width spring.
STANDARD_BUTTON_GROUP_WIDTH: Motion = SPRING_STANDARD_FAST_SPATIAL

# Search bar — outer margin on focus, 24dp <-> 12dp.
# md.comp.search-bar.contained.motion.spring names a fast spatial spring, and
# contained is the expressive variant, so the expressive curve is the faithful
# reading. Its 9.21% overshoot is an intended bounce, not ringing.
SEARCH_BAR_FOCUS_MARGIN: Motion = EXPRESSIVE_FAST_SPATIAL

__all__ = [
    "EXPRESSIVE_FAST_SPATIAL",
    "EXPRESSIVE_DEFAULT_SPATIAL",
    "EXPRESSIVE_SLOW_SPATIAL",
    "EXPRESSIVE_FAST_EFFECTS",
    "EXPRESSIVE_DEFAULT_EFFECTS",
    "EXPRESSIVE_SLOW_EFFECTS",
    "STANDARD_FAST_SPATIAL",
    "STANDARD_DEFAULT_SPATIAL",
    "STANDARD_SLOW_SPATIAL",
    "STANDARD_FAST_EFFECTS",
    "STANDARD_DEFAULT_EFFECTS",
    "STANDARD_SLOW_EFFECTS",
    "SPRING_STANDARD_FAST_SPATIAL",
    "STANDARD_BUTTON_GROUP_WIDTH",
    "SEARCH_BAR_FOCUS_MARGIN",
]
