"""Tests for the Divider widget and DividerStyle."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nuiitivet.material.divider import Divider
from nuiitivet.material.styles.divider_style import DividerStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.rendering.sizing import Sizing


# ---------------------------------------------------------------------------
# DividerStyle
# ---------------------------------------------------------------------------


def test_divider_style_defaults() -> None:
    style = DividerStyle()
    assert style.color == ColorRole.OUTLINE_VARIANT
    assert style.thickness == 1
    assert style.inset_left == 0
    assert style.inset_right == 0


def test_divider_style_copy_with_color() -> None:
    style = DividerStyle().copy_with(color="#FF0000")
    assert style.color == "#FF0000"
    assert style.thickness == 1  # unchanged


def test_divider_style_copy_with_thickness() -> None:
    style = DividerStyle().copy_with(thickness=4)
    assert style.thickness == 4
    assert style.inset_left == 0  # unchanged


def test_divider_style_copy_with_insets() -> None:
    style = DividerStyle().copy_with(inset_left=16, inset_right=8)
    assert style.inset_left == 16
    assert style.inset_right == 8


def test_divider_style_is_immutable() -> None:
    style = DividerStyle()
    with pytest.raises((AttributeError, TypeError)):
        style.thickness = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Divider – sizing defaults
# ---------------------------------------------------------------------------


def test_divider_horizontal_default_sizing() -> None:
    d = Divider()
    assert d.width_sizing.kind == "flex"
    assert d.height_sizing.kind == "fixed"
    assert d.height_sizing.value == 1  # default thickness


def test_divider_vertical_default_sizing() -> None:
    d = Divider(orientation="vertical")
    assert d.width_sizing.kind == "fixed"
    assert d.width_sizing.value == 1  # default thickness
    assert d.height_sizing.kind == "flex"


def test_divider_horizontal_custom_thickness() -> None:
    d = Divider(style=DividerStyle(thickness=4))
    assert d.height_sizing.kind == "fixed"
    assert d.height_sizing.value == 4


def test_divider_vertical_custom_thickness() -> None:
    d = Divider(orientation="vertical", style=DividerStyle(thickness=3))
    assert d.width_sizing.kind == "fixed"
    assert d.width_sizing.value == 3


def test_divider_explicit_width_override() -> None:
    d = Divider(width=Sizing.fixed(200))
    assert d.width_sizing.kind == "fixed"
    assert d.width_sizing.value == 200


def test_divider_explicit_height_override() -> None:
    d = Divider(height=Sizing.fixed(50))
    assert d.height_sizing.kind == "fixed"
    assert d.height_sizing.value == 50


# ---------------------------------------------------------------------------
# Divider – preferred_size
# ---------------------------------------------------------------------------


def test_divider_horizontal_preferred_size_with_max() -> None:
    d = Divider()
    w, h = d.preferred_size(max_width=300, max_height=100)
    assert w == 300  # flex → uses max_width
    assert h == 1  # fixed thickness


def test_divider_vertical_preferred_size_with_max() -> None:
    d = Divider(orientation="vertical")
    w, h = d.preferred_size(max_width=100, max_height=200)
    assert w == 1  # fixed thickness
    assert h == 200  # flex → uses max_height


def test_divider_preferred_size_no_max() -> None:
    d = Divider()
    w, h = d.preferred_size()
    assert w == 0  # flex with no constraint → 0
    assert h == 1  # fixed


# ---------------------------------------------------------------------------
# Divider – paint (canvas=None guard)
# ---------------------------------------------------------------------------


def test_divider_paint_none_canvas_does_not_raise() -> None:
    d = Divider()
    d.paint(None, 0, 0, 200, 1)
    assert d.last_rect == (0, 0, 200, 1)


def test_divider_paint_sets_last_rect() -> None:
    d = Divider()
    d.paint(None, 10, 20, 100, 1)
    assert d.last_rect == (10, 20, 100, 1)


# ---------------------------------------------------------------------------
# Divider – paint (with mock canvas & color resolution)
# ---------------------------------------------------------------------------


def _make_canvas():
    return MagicMock()


def test_divider_paint_calls_draw_rect() -> None:
    d = Divider()
    canvas = _make_canvas()

    with (
        patch("nuiitivet.material.divider.resolve_color_to_rgba", return_value=(100, 100, 100, 255)),
        patch("nuiitivet.material.divider.make_paint", return_value=MagicMock()),
        patch("nuiitivet.material.divider.make_rect", return_value=MagicMock()) as mock_rect,
    ):
        d.paint(canvas, 0, 0, 200, 1)
        mock_rect.assert_called_once_with(0, 0, 200, 1)
        canvas.drawRect.assert_called_once()


def test_divider_paint_horizontal_inset_applied() -> None:
    style = DividerStyle(inset_left=16, inset_right=8)
    d = Divider(style=style)
    canvas = _make_canvas()

    with (
        patch("nuiitivet.material.divider.resolve_color_to_rgba", return_value=(0, 0, 0, 255)),
        patch("nuiitivet.material.divider.make_paint", return_value=MagicMock()),
        patch("nuiitivet.material.divider.make_rect", return_value=MagicMock()) as mock_rect,
    ):
        d.paint(canvas, 0, 0, 200, 1)
        # x offset by inset_left, width reduced by both insets
        mock_rect.assert_called_once_with(16, 0, 176, 1)


def test_divider_paint_vertical_inset_applied() -> None:
    style = DividerStyle(inset_left=8, inset_right=8)
    d = Divider(orientation="vertical", style=style)
    canvas = _make_canvas()

    with (
        patch("nuiitivet.material.divider.resolve_color_to_rgba", return_value=(0, 0, 0, 255)),
        patch("nuiitivet.material.divider.make_paint", return_value=MagicMock()),
        patch("nuiitivet.material.divider.make_rect", return_value=MagicMock()) as mock_rect,
    ):
        d.paint(canvas, 0, 0, 1, 100)
        # y offset by inset_left, height reduced by both insets
        mock_rect.assert_called_once_with(0, 8, 1, 84)


def test_divider_paint_skipped_when_inset_exceeds_size() -> None:
    style = DividerStyle(inset_left=100, inset_right=100)
    d = Divider(style=style)
    canvas = _make_canvas()

    with (
        patch("nuiitivet.material.divider.resolve_color_to_rgba", return_value=(0, 0, 0, 255)),
        patch("nuiitivet.material.divider.make_paint", return_value=MagicMock()),
        patch("nuiitivet.material.divider.make_rect", return_value=MagicMock()) as mock_rect,
    ):
        d.paint(canvas, 0, 0, 50, 1)
        mock_rect.assert_not_called()
        canvas.drawRect.assert_not_called()


def test_divider_paint_skipped_when_color_unresolved() -> None:
    d = Divider()
    canvas = _make_canvas()

    with patch("nuiitivet.material.divider.resolve_color_to_rgba", return_value=None):
        d.paint(canvas, 0, 0, 100, 1)
        canvas.drawRect.assert_not_called()


# ---------------------------------------------------------------------------
# Divider – public API from material package
# ---------------------------------------------------------------------------


def test_divider_importable_from_material() -> None:
    from nuiitivet.material import Divider as MaterialDivider

    assert MaterialDivider is Divider


# ---------------------------------------------------------------------------
# Divider – padding
# ---------------------------------------------------------------------------


def test_divider_default_padding_is_zero() -> None:
    d = Divider()
    assert d.padding == (0, 0, 0, 0)


def test_divider_padding_scalar() -> None:
    d = Divider(padding=8)
    assert d.padding == (8, 8, 8, 8)


def test_divider_padding_tuple() -> None:
    d = Divider(padding=(4, 8, 4, 8))
    assert d.padding == (4, 8, 4, 8)
