"""
Tests for ClipModifier behavior with layout widgets.

Verifies that:
- Layout widgets (Column, Row) do not clip by default.
- Applying .clip() modifier enables clipping.
- MaterialContainer behaves correctly with .clip().
"""

from unittest.mock import MagicMock
import unittest
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material.card import Card
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.layout.row import Row
from nuiitivet.widgets import TextBase as Text
from nuiitivet.rendering import Sizing
from nuiitivet.modifiers import clip
from nuiitivet.rendering.skia import skia_module


def _skip_if_no_skia(test_case):
    if skia_module.get_skia(raise_if_missing=False) is None:
        test_case.skipTest("skia-python is required for clipping tests")


def test_column_default_no_clip():
    """Column does not clip by default."""
    col = Column(width=Sizing.fixed(100), height=Sizing.fixed(50))
    t1 = Text("Large", width=Sizing.fixed(80), height=Sizing.fixed(60))
    col.add_child(t1)

    canvas = MagicMock()
    col.paint(canvas, 0, 0, 100, 50)

    # No clipping calls
    canvas.clipRect.assert_not_called()
    # Child rendered at full size
    assert t1.last_rect == (0, 0, 80, 60)


def test_column_with_clip_modifier():
    """Column with .clip() modifier applies clipping."""
    _skip_if_no_skia(unittest.TestCase())
    col_inner = Column(width=Sizing.fixed(100), height=Sizing.fixed(50))
    col = col_inner.modifier(clip())
    t1 = Text("Large", width=Sizing.fixed(80), height=Sizing.fixed(60))
    # Access the inner widget to add child
    col.children[0].add_child(t1)

    canvas = MagicMock()
    canvas.save = MagicMock(return_value=1)

    col.paint(canvas, 0, 0, 100, 50)

    # Clipping applied
    canvas.clipRect.assert_called()
    # Child rendered, but visually clipped by canvas state (not verified here directly, but clipRect called)
    # Note: _last_rect might still be full size depending on implementation,
    # but the canvas clip ensures visual clipping.
    assert t1.last_rect == (0, 0, 80, 60)


def test_row_default_no_clip():
    """Row does not clip by default."""
    row = Row(width=Sizing.fixed(100), height=Sizing.fixed(50))
    t1 = Text("Wide", width=Sizing.fixed(120), height=Sizing.fixed(40))
    row.add_child(t1)

    canvas = MagicMock()
    row.paint(canvas, 0, 0, 100, 50)

    canvas.clipRect.assert_not_called()
    assert t1.last_rect == (0, 0, 120, 40)


def test_row_with_clip_modifier():
    """Row with .clip() modifier applies clipping."""
    _skip_if_no_skia(unittest.TestCase())
    row_inner = Row(width=Sizing.fixed(100), height=Sizing.fixed(50))
    row = row_inner.modifier(clip())
    t1 = Text("Wide", width=Sizing.fixed(120), height=Sizing.fixed(40))
    row.children[0].add_child(t1)

    canvas = MagicMock()
    canvas.save = MagicMock(return_value=1)

    row.paint(canvas, 0, 0, 100, 50)

    canvas.clipRect.assert_called()
    assert t1.last_rect == (0, 0, 120, 40)


def test_container_default_no_clip():
    """Card does not clip by default (if radius is 0)."""
    t = Text("Large", width=Sizing.fixed(120), height=Sizing.fixed(60))
    c = Card(
        child=t,
        width=Sizing.fixed(100),
        height=Sizing.fixed(50),
        style=CardStyle.filled().copy_with(border_radius=0),
    )

    canvas = MagicMock()
    c.paint(canvas, 0, 0, 100, 50)

    # Box might call save/restore for other reasons (shadows), but shouldn't call clipRect for content
    # unless border_radius is set (which it isn't here)
    canvas.clipRect.assert_not_called()
    assert t.last_rect == (0, 0, 120, 60)


def test_container_with_clip_modifier():
    """Card with .clip() modifier applies clipping."""
    _skip_if_no_skia(unittest.TestCase())
    t = Text("Large", width=Sizing.fixed(120), height=Sizing.fixed(60))
    c_inner = Card(
        child=t,
        width=Sizing.fixed(100),
        height=Sizing.fixed(50),
        style=CardStyle.filled().copy_with(border_radius=0),
    )
    c = c_inner.modifier(clip())
    # Card returns a Box, and ClipModifier modifies Box in-place
    # so c is the Box itself, not a wrapper.

    canvas = MagicMock()
    canvas.save = MagicMock(return_value=1)

    c.paint(canvas, 0, 0, 100, 50)

    canvas.clipRect.assert_called()
    assert t.last_rect == (0, 0, 120, 60)


def test_clip_preserves_weight_sizing_on_container():
    """Wrapping a non-Box widget keeps its weight sizing on the wrapper."""
    inner = Container(width=Sizing.weight(), height=Sizing.weight())
    wrapper = inner.modifier(clip())

    # Container is not a Box, so it must have been wrapped.
    assert wrapper is not inner
    assert wrapper.children[0] is inner
    assert wrapper.clip_content is True

    assert wrapper.width_sizing == Sizing.weight()
    assert wrapper.height_sizing == Sizing.weight()


def test_clip_preserves_fixed_sizing_on_column():
    """The wrapper inherits fixed sizing instead of collapsing to auto."""
    inner = Column(width=Sizing.fixed(100), height=Sizing.fixed(50))
    wrapper = inner.modifier(clip())

    assert wrapper is not inner
    assert wrapper.width_sizing == inner.width_sizing
    assert wrapper.height_sizing == inner.height_sizing


def test_clip_on_box_does_not_wrap():
    """Box-based widgets are clipped in place, so sizing is untouched."""
    card = Card(
        child=Text("Content"),
        width=Sizing.weight(),
        height=Sizing.fixed(50),
        style=CardStyle.filled().copy_with(border_radius=0),
    )
    result = card.modifier(clip())

    assert result is card
    assert result.clip_content is True
    assert result.width_sizing == Sizing.weight()
    assert result.height_sizing == Sizing.fixed(50)
