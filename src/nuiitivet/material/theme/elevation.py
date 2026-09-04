"""Material Design 3 elevation level -> shadow mapping.

This module belongs to the Material Design layer. It translates the MD3
concept of *elevation level* (0-5) into concrete ``Shadow`` layers
understood by the rendering layer.

MD3 draws each level as **two** stacked box-shadow layers: a tight, darker
*key* shadow at alpha 0.30, and a wide, softer *ambient* shadow at alpha 0.15
that carries a spread. The values below are the upstream box-shadow tokens
transcribed verbatim.

Two things the table deliberately does not do:

- It does not derive the geometry from the level number. The level is an index,
  not a dp value (levels 0-5 are 0/1/3/6/8/12 dp), and neither the offsets nor
  the blurs track dp linearly.
- It does not collapse the two layers into one. The ambient layer's spread is
  what makes low elevations visible at all: without it the opaque container
  paints over everything but the blur tail.

See: https://m3.material.io/styles/elevation/overview
"""

from __future__ import annotations

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.rendering.shadow import NO_SHADOWS, Shadow, Shadows

# The two layers' colors, from the upstream stylesheet.
_KEY = (ColorRole.SHADOW, 0.30)
_AMBIENT = (ColorRole.SHADOW, 0.15)

#: MD3 elevation level -> shadow layers, transcribed from the upstream CSS
#: box-shadow tokens. Ambient first so the key shadow stacks on top of it.
_MD3_SHADOWS: dict[int, Shadows] = {
    0: NO_SHADOWS,
    1: (
        Shadow(_AMBIENT, blur_radius=3.0, offset=(0.0, 1.0), spread_radius=1.0),
        Shadow(_KEY, blur_radius=2.0, offset=(0.0, 1.0)),
    ),
    2: (
        Shadow(_AMBIENT, blur_radius=6.0, offset=(0.0, 2.0), spread_radius=2.0),
        Shadow(_KEY, blur_radius=2.0, offset=(0.0, 1.0)),
    ),
    3: (
        Shadow(_AMBIENT, blur_radius=8.0, offset=(0.0, 4.0), spread_radius=3.0),
        Shadow(_KEY, blur_radius=3.0, offset=(0.0, 1.0)),
    ),
    4: (
        Shadow(_AMBIENT, blur_radius=10.0, offset=(0.0, 6.0), spread_radius=4.0),
        Shadow(_KEY, blur_radius=3.0, offset=(0.0, 2.0)),
    ),
    5: (
        Shadow(_AMBIENT, blur_radius=12.0, offset=(0.0, 8.0), spread_radius=6.0),
        Shadow(_KEY, blur_radius=4.0, offset=(0.0, 4.0)),
    ),
}


def elevation_shadows(level: int) -> Shadows:
    """Return the shadows for the given MD3 elevation level.

    The result feeds the ``shadows()`` modifier directly::

        widget.modifier(nv.shadows(nv.elevation_shadows(2)))

    Args:
        level: MD3 elevation level, clamped to the range 0-5.

    Returns:
        A tuple of ``Shadow`` layers ordered back to front (ambient, then
        key). Level 0 returns an empty tuple, which draws no shadow.
    """
    return _MD3_SHADOWS[max(0, min(5, level))]
