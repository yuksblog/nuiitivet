"""Tests for Scrollable scrollbar placement modes (overlay vs inline).

Placement is owned by ``ScrollableStyle.scrollbar_overlay`` and is fully
decoupled from temporal behavior (``ScrollbarBehavior.auto_hide``):
- scrollbar_overlay=True  -> overlay (do not reserve viewport space)
- scrollbar_overlay=False -> inline (reserve scrollbar thickness + padding)

All four combinations of overlay x auto_hide are exercised below.
"""

import pytest

from nuiitivet.scrolling import ScrollController, ScrollableStyle, ScrollbarStyle
from nuiitivet.layout.scrollable import VerticalScrollable, HorizontalScrollable
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.scrollbar import ScrollbarBehavior


def _paint(scroller, width, height):
    """Paint a scroller with skia/text side effects stubbed out."""
    from nuiitivet.widgets import scrollbar as sb_mod
    from nuiitivet.widgets import text as text_mod

    orig_sb_get_skia = sb_mod.get_skia
    orig_text_paint = text_mod.TextBase.paint
    sb_mod.get_skia = lambda raise_if_missing=False: None
    text_mod.TextBase.paint = lambda self, canvas, x, y, w, h: None
    try:
        scroller.paint(canvas=None, x=0, y=0, width=width, height=height)
    finally:
        sb_mod.get_skia = orig_sb_get_skia
        text_mod.TextBase.paint = orig_text_paint


@pytest.mark.parametrize("auto_hide", [True, False])
def test_overlay_does_not_reserve_space(auto_hide):
    """scrollbar_overlay=True -> viewport width is NOT reduced, for any auto_hide."""
    child = Column([Text(f"Item {i}") for i in range(50)])
    scroller = VerticalScrollable(
        child=child,
        controller=ScrollController(),
        scrollbar_behavior=ScrollbarBehavior(auto_hide=auto_hide),
        scrollbar_style=ScrollbarStyle(thickness=12),
        style=ScrollableStyle(scrollbar_padding=2, scrollbar_overlay=True),
    )
    _paint(scroller, width=200, height=150)
    vp = scroller._viewport.viewport_rect
    assert vp is not None
    assert vp[2] == 200


@pytest.mark.parametrize("auto_hide", [True, False])
def test_inline_reserves_space_vertical(auto_hide):
    """scrollbar_overlay=False -> viewport width reduced by thickness+padding, for any auto_hide."""
    child = Column([Text(f"Item {i}") for i in range(50)])
    scroller = VerticalScrollable(
        child=child,
        controller=ScrollController(),
        scrollbar_behavior=ScrollbarBehavior(auto_hide=auto_hide),
        scrollbar_style=ScrollbarStyle(thickness=10),
        style=ScrollableStyle(scrollbar_padding=3, scrollbar_overlay=False),
    )
    _paint(scroller, width=240, height=180)
    vp = scroller._viewport.viewport_rect
    assert vp is not None
    expected_w = max(0, 240 - scroller._scrollbar.thickness - scroller._scrollbar_padding[2])
    assert vp[2] == expected_w


@pytest.mark.parametrize("auto_hide", [True, False])
def test_inline_reserves_space_horizontal(auto_hide):
    """Horizontal inline mode reduces viewport height by thickness+padding, for any auto_hide."""
    cards = [Text(f"Card {i}") for i in range(20)]
    scroller = HorizontalScrollable(
        child=Row(cards, gap=4),
        scrollbar_behavior=ScrollbarBehavior(auto_hide=auto_hide),
        height=60,
        scrollbar_style=ScrollbarStyle(thickness=10),
        style=ScrollableStyle(scrollbar_padding=4, scrollbar_overlay=False),
    )
    _paint(scroller, width=400, height=60)
    vp = scroller._viewport.viewport_rect
    assert vp is not None
    expected_h = max(0, 60 - scroller._scrollbar.thickness - scroller._scrollbar_padding[3])
    assert vp[3] == expected_h
