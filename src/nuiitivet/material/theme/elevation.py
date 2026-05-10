"""Material Design 3 elevation level → ShadowParams mapping.

This module belongs to the Material Design layer. It translates the MD3
concept of *elevation level* (0–5) into concrete ``ShadowParams`` understood
by the rendering layer.

Reference values are derived from the MD3 specification and Flutter's
Material implementation:

- ``sigma`` ≈ ``level / 2`` — approximates Flutter's key-shadow sigma for each
  elevation level (level 3 / 6 dp → sigma ≈ 3).
- ``offset_y = level`` — slight downward shift creates a natural depth cue.
- ``alpha`` ranges from 0.0 (no shadow) to 0.30 (subtle, not overpowering).

See: https://m3.material.io/styles/elevation/overview
"""

from __future__ import annotations

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.rendering.shadow import ShadowParams, NO_SHADOW

# MD3 elevation level → ShadowParams lookup table.
# Key: elevation level (int, 0–5)
# Value: ShadowParams with Skia-level rendering parameters
_MD3_SHADOWS: dict[int, ShadowParams] = {
    0: NO_SHADOW,
    1: ShadowParams(sigma=1.0, offset=(0.0, 1.0), color=(ColorRole.SHADOW, 0.20)),
    2: ShadowParams(sigma=2.0, offset=(0.0, 2.0), color=(ColorRole.SHADOW, 0.25)),
    3: ShadowParams(sigma=3.0, offset=(0.0, 3.0), color=(ColorRole.SHADOW, 0.30)),
    4: ShadowParams(sigma=4.0, offset=(0.0, 4.0), color=(ColorRole.SHADOW, 0.30)),
    5: ShadowParams(sigma=5.0, offset=(0.0, 5.0), color=(ColorRole.SHADOW, 0.30)),
}


def md3_elevation_to_shadow(level: int) -> ShadowParams:
    """Return ``ShadowParams`` for the given MD3 elevation level.

    Args:
        level: MD3 elevation level, clamped to the range 0–5.

    Returns:
        ``ShadowParams`` with Skia sigma, offset and color appropriate for the
        requested elevation level. Level 0 returns :data:`NO_SHADOW`.
    """
    return _MD3_SHADOWS[max(0, min(5, level))]
