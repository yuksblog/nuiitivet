"""Tests for Scroller scrollbar display modes (overlay vs reserve-always).

These confirm Phase 1 behaviour:
- auto_hide=True -> overlay (do not reserve viewport space)
- auto_hide=False -> reserve-always (always reserve scrollbar thickness)
"""

from nuiitivet.scrolling import ScrollController
from nuiitivet.layout.scroller import Scroller
from nuiitivet.layout.column import Column
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.scrollbar import ScrollbarBehavior


def test_scroller_overlay_when_auto_hide_true():
    """When auto_hide=True (overlay), viewport area should NOT be reduced by scrollbar thickness."""
    child = Column([Text(f"Item {i}") for i in range(50)])
    controller = ScrollController()
    scroller = Scroller(
        child=child,
        scroll_controller=controller,
        scrollbar=ScrollbarBehavior(auto_hide=True),
        scrollbar_thickness=12,
        scrollbar_padding=2,
    )
    from nuiitivet.widgets import scrollbar as sb_mod

    orig_sb_get_skia = sb_mod.get_skia
    sb_mod.get_skia = lambda raise_if_missing=False: None
    from nuiitivet.widgets import text as text_mod

    orig_text_paint = text_mod.TextBase.paint
    text_mod.TextBase.paint = lambda self, canvas, x, y, w, h: None
    try:
        scroller.paint(canvas=None, x=0, y=0, width=200, height=150)
    finally:
        sb_mod.get_skia = orig_sb_get_skia
        text_mod.TextBase.paint = orig_text_paint
    vp = scroller._viewport.viewport_rect
    assert vp is not None
    assert vp[2] == 200


def test_scroller_reserve_always_when_auto_hide_false():
    """When auto_hide=False (reserve-always), viewport area should be reduced by scrollbar thickness+padding."""
    child = Column([Text(f"Item {i}") for i in range(50)])
    controller = ScrollController()
    cfg = ScrollbarBehavior(auto_hide=False)
    scroller = Scroller(
        child=child,
        scroll_controller=controller,
        scrollbar=cfg,
        scrollbar_thickness=10,
        scrollbar_padding=3,
    )
    from nuiitivet.widgets import scrollbar as sb_mod

    orig_sb_get_skia = sb_mod.get_skia
    sb_mod.get_skia = lambda raise_if_missing=False: None
    from nuiitivet.widgets import text as text_mod

    orig_text_paint = text_mod.TextBase.paint
    text_mod.TextBase.paint = lambda self, canvas, x, y, w, h: None
    try:
        scroller.paint(canvas=None, x=0, y=0, width=240, height=180)
    finally:
        sb_mod.get_skia = orig_sb_get_skia
        text_mod.TextBase.paint = orig_text_paint
    vp = scroller._viewport.viewport_rect
    assert vp is not None
    sb = scroller._scrollbar
    assert sb is not None
    expected_w = max(0, 240 - sb.thickness - sb.padding[2])
    assert vp[2] == expected_w


def test_scroller_reserve_always_horizontal_reduces_height():
    """For horizontal scrollers with auto_hide=False the viewport height
    should be reduced by thickness + padding (reserve-always).
    """
    from nuiitivet.layout.row import Row

    cards = [Text(f"Card {i}") for i in range(20)]
    cfg = ScrollbarBehavior(auto_hide=False)
    scroller = Scroller(
        child=Row(cards, gap=4),
        scrollbar=cfg,
        direction="horizontal",
        height=60,
        scrollbar_thickness=10,
        scrollbar_padding=4,
    )
    from nuiitivet.widgets import scrollbar as sb_mod
    from nuiitivet.widgets import text as text_mod

    orig_sb_get_skia = sb_mod.get_skia
    sb_mod.get_skia = lambda raise_if_missing=False: None
    orig_text_paint = text_mod.TextBase.paint
    text_mod.TextBase.paint = lambda self, canvas, x, y, w, h: None
    try:
        scroller.paint(canvas=None, x=0, y=0, width=400, height=60)
        vp = scroller._viewport.viewport_rect
        assert vp is not None
        sb = scroller._scrollbar
        assert sb is not None
        expected_h = max(0, 60 - sb.thickness - sb.padding[3])
        assert vp[3] == expected_h
    finally:
        sb_mod.get_skia = orig_sb_get_skia
        text_mod.TextBase.paint = orig_text_paint
