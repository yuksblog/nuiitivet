"""Tests for shared_paint: one skia.Paint per distinct set of settings."""

from unittest.mock import patch

import pytest

from nuiitivet.rendering.skia import color as color_module
from nuiitivet.rendering.skia import make_paint, rgba_to_skia_color, shared_paint
from nuiitivet.rendering.skia.skia_module import get_skia

skia = get_skia(raise_if_missing=False)
pytestmark = pytest.mark.skipif(skia is None, reason="skia backend not available")

RED = rgba_to_skia_color((255, 0, 0, 255))
BLUE = rgba_to_skia_color((0, 0, 255, 255))


def test_same_settings_return_the_same_paint() -> None:
    assert shared_paint(RED) is shared_paint(RED)
    assert shared_paint(RED, "stroke", 2.0) is shared_paint(RED, "stroke", 2.0)


def test_each_setting_is_part_of_the_identity() -> None:
    base = shared_paint(RED, "stroke", 2.0)

    assert shared_paint(BLUE, "stroke", 2.0) is not base
    assert shared_paint(RED, "fill", 2.0) is not base
    assert shared_paint(RED, "stroke", 3.0) is not base
    assert shared_paint(RED, "stroke", 2.0, aa=False) is not base
    assert shared_paint(RED, "stroke", 2.0, stroke_cap="round") is not base


def test_the_paint_is_configured_as_make_paint_would() -> None:
    shared = shared_paint(BLUE, "stroke", 3.0, stroke_cap="round")
    made = make_paint(color=BLUE, style="stroke", stroke_width=3.0, stroke_cap="round")

    assert shared.getColor() == made.getColor()
    assert shared.getStyle() == made.getStyle()
    assert shared.getStrokeWidth() == made.getStrokeWidth()
    assert shared.getStrokeCap() == made.getStrokeCap()
    assert shared.isAntiAlias() == made.isAntiAlias()


def test_a_repeat_builds_no_paint() -> None:
    shared_paint(RED, "stroke", 5.0)
    with patch.object(color_module, "make_paint", wraps=color_module.make_paint) as made:
        shared_paint(RED, "stroke", 5.0)

    assert made.call_count == 0


def test_a_full_table_starts_over() -> None:
    with patch.object(color_module, "_SHARED_PAINT_LIMIT", 2), patch.dict(color_module._shared_paints, clear=True):
        first = shared_paint(RED)
        shared_paint(BLUE)
        shared_paint(RED, "stroke")

        assert shared_paint(RED) is not first


def test_an_unhashable_colour_is_built_each_time() -> None:
    colour = [255, 0, 0, 255]

    first = shared_paint(colour)  # type: ignore[arg-type]

    assert first is not None
    assert shared_paint(colour) is not first  # type: ignore[arg-type]
