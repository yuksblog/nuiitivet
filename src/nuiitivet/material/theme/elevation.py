"""Material Design 3 elevation level -> shadow layer mapping.

This module belongs to the Material Design layer. It translates the MD3
concept of *elevation level* (0-5) into concrete ``ShadowParams`` layers
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
from nuiitivet.rendering.shadow import NO_SHADOW, ShadowLayers, ShadowParams

# Alpha the two layers are drawn at, from the upstream stylesheet.
_KEY_ALPHA = 0.30
_AMBIENT_ALPHA = 0.15

_KEY_COLOR = (ColorRole.SHADOW, _KEY_ALPHA)
_AMBIENT_COLOR = (ColorRole.SHADOW, _AMBIENT_ALPHA)

# MD3 elevation level -> shadow layers, as CSS box-shadow values.
# Key: elevation level (int, 0-5)
# Value: (key layer, ambient layer), each (offset_y, blur, spread) in px.
_MD3_BOX_SHADOWS: dict[int, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    1: ((1.0, 2.0, 0.0), (1.0, 3.0, 1.0)),
    2: ((1.0, 2.0, 0.0), (2.0, 6.0, 2.0)),
    3: ((1.0, 3.0, 0.0), (4.0, 8.0, 3.0)),
    4: ((2.0, 3.0, 0.0), (6.0, 10.0, 4.0)),
    5: ((4.0, 4.0, 0.0), (8.0, 12.0, 6.0)),
}


def _layers(level: int) -> ShadowLayers:
    key, ambient = _MD3_BOX_SHADOWS[level]
    key_y, key_blur, key_spread = key
    amb_y, amb_blur, amb_spread = ambient
    return (
        ShadowParams.from_css(0.0, amb_y, amb_blur, amb_spread, _AMBIENT_COLOR),
        ShadowParams.from_css(0.0, key_y, key_blur, key_spread, _KEY_COLOR),
    )


#: MD3 elevation level -> shadow layers, ambient first so the key shadow
#: stacks on top of it.
_MD3_SHADOWS: dict[int, ShadowLayers] = {level: _layers(level) for level in _MD3_BOX_SHADOWS}
_MD3_SHADOWS[0] = NO_SHADOW


def md3_elevation_to_shadow(level: int) -> ShadowLayers:
    """Return the shadow layers for the given MD3 elevation level.

    Args:
        level: MD3 elevation level, clamped to the range 0-5.

    Returns:
        A tuple of ``ShadowParams`` ordered back to front (ambient, then key).
        Level 0 returns :data:`NO_SHADOW`, an empty tuple.
    """
    return _MD3_SHADOWS[max(0, min(5, level))]
