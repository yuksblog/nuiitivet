"""The MD3 elevation shadow must keep its two-layer strength.

The defect these tests pin down: the elevation table used to emit a single
blurred layer whose sigma was the level *number*. That reads at roughly half
the spec's darkness and half its reach, and no single layer can reproduce the
spec at all -- the ambient layer's spread is what pushes darkness out past the
opaque card body, which is the only reason a level-1 shadow is visible.

So the assertions here are on sampled pixels, not on the table's numbers: a
regression to one layer, or a table rebuilt from the level number again, has to
show up as a measurably weaker profile.
"""

from __future__ import annotations

import dataclasses

import pytest

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.elevation import elevation_shadows
from nuiitivet.rendering.background_renderer import BackgroundRenderer
from nuiitivet.rendering.shadow import Shadow, Shadows, shadow_outsets

skia = pytest.importorskip("skia", reason="offscreen shadow sampling needs skia-python")


# The card the profiles below were sampled from: white on white, so the only
# darkness on the surface is the shadow itself.
_CARD_W = 120
_CARD_H = 70
_CORNER = 12.0
_PAD = 40  # slack around the card so no layer is clipped by the surface edge


def _concrete(layers: Shadows) -> Shadows:
    """Swap ``ColorRole.SHADOW`` for the value a Material theme resolves it to.

    The owner below is a stand-in, not a mounted widget, so ``Theme.of`` finds
    no Material theme and the role resolves to transparent. Baking in
    ``md.sys.color.shadow`` (``#000000``) keeps these tests measuring what they
    are about -- the layers' geometry and alpha -- and leaves the role wiring to
    the widget tests that assert on ``shadows`` directly.
    """
    return tuple(
        dataclasses.replace(layer, color=("#000000", layer.color[1]))
        if isinstance(layer.color, tuple) and layer.color[0] is ColorRole.SHADOW
        else layer
        for layer in layers
    )


class _Owner:
    """The minimum surface ``BackgroundRenderer`` reads from its owner."""

    def __init__(self, shadows: tuple[Shadow, ...], corner_radius: float) -> None:
        self._parent = None
        self._mounted = False
        self.bgcolor = None
        self.corner_radius = corner_radius
        self.corner_radii = (corner_radius,) * 4
        self.border_width = 0
        self.border_color = None
        self.shadows = shadows


def _sample_profile(
    shadows: tuple[Shadow, ...],
    *,
    direction: str,
    length: int,
) -> list[int]:
    """Render *shadows* under an opaque card and sample darkness outward.

    The card is drawn on top so the sampled pixels are only what survives
    outside its opaque body -- the same thing the eye sees.

    Args:
        shadows: The layers to draw.
        direction: ``"down"`` samples below the bottom edge, ``"right"``
            samples out from the right edge.
        length: How many pixels to sample.

    Returns:
        Darkness per pixel, 0 (white) to 255 (black), moving outward.
    """
    surface = skia.Surface(_CARD_W + _PAD * 2, _CARD_H + _PAD * 2)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)

    renderer = BackgroundRenderer(_Owner(_concrete(shadows), _CORNER))
    renderer.paint_shadow_and_background(canvas, _PAD, _PAD, _CARD_W, _CARD_H)

    # The opaque card body, painted over the shadow.
    body = skia.RRect.MakeRectXY(
        skia.Rect.MakeXYWH(_PAD, _PAD, _CARD_W, _CARD_H), _CORNER, _CORNER
    )
    paint = skia.Paint(Color=skia.ColorWHITE, AntiAlias=True)
    canvas.drawRRect(body, paint)

    image = surface.makeImageSnapshot()
    pixels = image.toarray(colorType=skia.kRGBA_8888_ColorType)

    profile: list[int] = []
    for step in range(length):
        if direction == "down":
            row = _PAD + _CARD_H + step
            col = _PAD + _CARD_W // 2
        else:
            row = _PAD + _CARD_H // 2
            col = _PAD + _CARD_W + step
        profile.append(255 - int(pixels[row][col][0]))
    return profile


# Darkness below the bottom edge, 0px..13px, as rendered from the MD3 tokens.
# Recorded from this suite; the tolerance below is what makes them a guard
# against a structural regression rather than a lock on exact Skia output.
_EXPECTED_DOWN = {
    1: [79, 45, 18, 6, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    3: [78, 59, 43, 33, 28, 24, 21, 17, 14, 11, 8, 6, 4, 2],
}

_TOLERANCE = 12


@pytest.mark.parametrize("level", sorted(_EXPECTED_DOWN))
def test_elevation_profile_matches_the_md3_tokens(level: int) -> None:
    profile = _sample_profile(elevation_shadows(level), direction="down", length=14)
    expected = _EXPECTED_DOWN[level]

    drift = [abs(a - b) for a, b in zip(profile, expected)]
    assert max(drift) <= _TOLERANCE, (
        f"level {level} shadow profile drifted from the MD3 tokens\n"
        f"  sampled:  {profile}\n"
        f"  expected: {expected}"
    )


def test_every_level_draws_two_layers() -> None:
    """Levels 1-5 are a key layer over a wider ambient one; level 0 draws nothing."""
    assert elevation_shadows(0) == ()
    for level in range(1, 6):
        layers = elevation_shadows(level)
        assert len(layers) == 2, f"level {level} must keep both MD3 shadow layers"
        ambient, key = layers
        assert ambient.spread_radius > 0.0, f"level {level} ambient layer lost its spread"
        assert ambient.blur_radius > key.blur_radius, f"level {level} ambient layer must be the softer one"


def test_level_1_reaches_sideways_past_the_card_body() -> None:
    """The ambient spread is what makes a level-1 shadow visible at all.

    Without it the shadow rect is exactly the card rect, so the opaque body
    paints over everything but the blur tail and the fringe collapses to ~2px.
    """
    profile = _sample_profile(elevation_shadows(1), direction="right", length=6)

    assert profile[0] >= 35, f"level 1 has no darkness at the edge: {profile}"
    fringe = sum(1 for value in profile if value > 0)
    assert fringe >= 4, f"level 1 sideways fringe is only {fringe}px: {profile}"


def test_outsets_cover_the_whole_profile() -> None:
    """The paint cache must reserve room for every layer, spread included.

    An outset short of the drawn extent clips the shadow at the cache edge.
    """
    for level in range(1, 6):
        layers = elevation_shadows(level)
        left, top, right, bottom = shadow_outsets(layers)
        for layer in layers:
            reach = max(4.0, layer.blur_radius * 1.5) + layer.spread_radius
            dx, dy = layer.offset
            assert left >= reach - dx
            assert right >= reach + dx
            assert top >= reach - dy
            assert bottom >= reach + dy
