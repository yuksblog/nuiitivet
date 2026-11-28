"""What a Box draws on repeated paints, where it keeps the border and clip between visits."""

from typing import Any, Tuple

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.modifiers.background import background
from nuiitivet.testing import mount
from nuiitivet.widgets.box import Box

skia = pytest.importorskip("skia")

_W, _H = 60, 40


def _paint(box: Box, x: int = 0, y: int = 0) -> Any:
    surface = skia.Surface(_W + 20, _H + 20)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    box.paint(canvas, x, y, _W, _H)
    return surface.makeImageSnapshot()


def _rgb(image: Any, x: int, y: int) -> Tuple[int, int, int]:
    pixels = image.convert(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType).toarray()
    r, g, b, _a = (int(v) for v in pixels[y, x])
    return (r, g, b)


def _box(**kwargs) -> Box:
    box = Box(width=_W, height=_H, **kwargs)
    box.layout(_W, _H)
    box.set_layout_rect(0, 0, _W, _H)
    return box


def test_a_border_follows_its_colour_width_and_position():
    box = _box(border_width=2, border_color="#FF0000", corner_radius=6)
    with mount(box, leak_check="off"):
        assert _rgb(_paint(box), _W // 2, 0) == (255, 0, 0)

        box.border_color = "#0000FF"
        assert _rgb(_paint(box), _W // 2, 0) == (0, 0, 255)

        box.border_width = 6
        assert _rgb(_paint(box), _W // 2, 4) == (0, 0, 255)

        moved = _paint(box, 10, 10)
        assert _rgb(moved, _W // 2 + 10, 10) == (0, 0, 255)
        assert _rgb(moved, _W // 2, 0) == (255, 255, 255)


def test_a_rounded_clip_follows_the_radius_and_the_size():
    child = Container(width=_W, height=_H).modifier(background("#FF0000"))
    box = Box(child, width=_W, height=_H, corner_radius=4)
    box.clip_content = True
    box.layout(_W, _H)
    box.set_layout_rect(0, 0, _W, _H)
    with mount(box, leak_check="off"):
        assert _rgb(_paint(box), 2, 2) == (255, 0, 0)

        box.corner_radius = 16
        assert _rgb(_paint(box), 2, 2) == (255, 255, 255)
        assert _rgb(_paint(box), _W // 2, _H // 2) == (255, 0, 0)


def test_a_rounded_clip_reads_the_radii_a_subclass_answers():
    class Pill(Box):
        def corner_radii_pixels(self, width: int, height: int) -> Tuple[float, float, float, float]:
            r = height / 2.0
            return (r, r, r, r)

    child = Container(width=_W, height=_H).modifier(background("#FF0000"))
    box = Pill(child, width=_W, height=_H)
    box.clip_content = True
    box.layout(_W, _H)
    box.set_layout_rect(0, 0, _W, _H)
    with mount(box, leak_check="off"):
        assert _rgb(_paint(box), 4, 4) == (255, 255, 255)


def test_a_box_with_nothing_behind_its_content_records_no_image():
    bare = _box(border_width=1, border_color="#000000")
    filled = _box(background_color="#00FF00")
    with mount(Container(width=_W, height=_H), leak_check="off"):
        _paint(bare)
        _paint(filled)
    assert bare._paint_cache_snapshot is None
    assert filled._paint_cache_snapshot is not None


def test_a_theme_colour_border_follows_a_theme_change():
    box = _box(border_width=2, border_color=ColorRole.PRIMARY)
    with mount(box, theme=MaterialThemeFactory.light("#6750A4"), leak_check="off") as host:
        host.layout(_W, _H)
        before = _rgb(_paint(box), _W // 2, 0)
        host.push_theme(MaterialThemeFactory.light("#00AA00"))
        after = _rgb(_paint(box), _W // 2, 0)
    assert before != after
