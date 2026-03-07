from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import IconButton
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.toolbar import DockedToolbar, FloatingToolbar
from nuiitivet.material.styles.button_style import IconButtonStyle
from nuiitivet.widgets.box import Box


def test_icon_button_vibrant_style_factories() -> None:
    vibrant = IconButtonStyle.vibrant()
    filled_vibrant = IconButtonStyle.filled_vibrant()
    outlined_vibrant = IconButtonStyle.outlined_vibrant()
    tonal_vibrant = IconButtonStyle.tonal_vibrant()

    assert vibrant.foreground == ColorRole.ON_PRIMARY_CONTAINER
    assert vibrant.overlay_color == ColorRole.ON_PRIMARY_CONTAINER

    assert filled_vibrant.background == ColorRole.PRIMARY
    assert filled_vibrant.foreground == ColorRole.ON_PRIMARY

    assert outlined_vibrant.border_color == ColorRole.ON_PRIMARY_CONTAINER
    assert outlined_vibrant.border_width == 1.0

    assert tonal_vibrant.background == ColorRole.SURFACE_CONTAINER_HIGHEST
    assert tonal_vibrant.foreground == ColorRole.ON_SURFACE


def test_docked_toolbar_has_no_outer_padding() -> None:
    toolbar = DockedToolbar([IconButton("add")])
    content = toolbar.children[0]

    assert toolbar.padding == (0, 0, 0, 0)
    assert len(toolbar.children) == 1
    assert isinstance(content, Row)
    assert content.width_sizing.kind == "flex"


def test_floating_toolbar_accepts_outer_padding() -> None:
    toolbar = FloatingToolbar([IconButton("add")], padding=(12, 8, 12, 8))

    assert toolbar.padding == (12, 8, 12, 8)
    assert len(toolbar.children) == 1
    assert isinstance(toolbar.children[0], Box)
    assert toolbar.children[0].corner_radius == 9999


def test_floating_toolbar_vertical_orientation_uses_column() -> None:
    buttons = [IconButton("add"), IconButton("close")]
    toolbar = FloatingToolbar(buttons, orientation="vertical")
    inner = toolbar.children[0]

    assert isinstance(inner, Box)
    assert len(inner.children) == 1
    assert isinstance(inner.children[0], Column)
    assert inner.children[0].padding == (16, 12, 16, 12)


def test_floating_toolbar_padding_rule_is_shared_across_orientations() -> None:
    buttons_h = [IconButton("add"), IconButton("close")]
    buttons_v = [IconButton("add"), IconButton("close")]

    horizontal = FloatingToolbar(buttons_h, orientation="horizontal")
    vertical = FloatingToolbar(buttons_v, orientation="vertical")

    horizontal_content = horizontal.children[0].children[0]
    vertical_content = vertical.children[0].children[0]

    assert isinstance(horizontal_content, Row)
    assert isinstance(vertical_content, Column)
    assert horizontal_content.padding == vertical_content.padding
