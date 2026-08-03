from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import IconButton
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.toolbar import (
    DockedToolbar,
    HorizontalFloatingToolbar,
    VerticalFloatingToolbar,
)
from nuiitivet.material.styles.button_style import IconButtonStyle
from nuiitivet.material.text import Text
from nuiitivet.modifiers.tooltip import TooltipBox, tooltip
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
    toolbar = HorizontalFloatingToolbar([IconButton("add")], padding=(12, 8, 12, 8))

    assert toolbar.padding == (12, 8, 12, 8)
    assert len(toolbar.children) == 1
    assert isinstance(toolbar.children[0], Box)
    assert toolbar.children[0].corner_radius == 9999


def test_floating_toolbar_vertical_orientation_uses_column() -> None:
    buttons = [IconButton("add"), IconButton("close")]
    toolbar = VerticalFloatingToolbar(buttons)
    # The edge inset is measured from the buttons, which is only possible once
    # they are attached -- so it lands on the first measure, not at construction
    # time. Measuring is also where the toolbar reads its style from the theme.
    toolbar.mount(None)
    toolbar.preferred_size()
    inner = toolbar.children[0]

    assert isinstance(inner, Box)
    assert len(inner.children) == 1
    assert isinstance(inner.children[0], Column)
    assert inner.children[0].padding == (16, 12, 16, 12)


def test_floating_toolbar_padding_rule_is_shared_across_orientations() -> None:
    buttons_h = [IconButton("add"), IconButton("close")]
    buttons_v = [IconButton("add"), IconButton("close")]

    horizontal = HorizontalFloatingToolbar(buttons_h)
    vertical = VerticalFloatingToolbar(buttons_v)
    horizontal.mount(None)
    vertical.mount(None)
    horizontal.preferred_size()
    vertical.preferred_size()

    horizontal_content = horizontal.children[0].children[0]
    vertical_content = vertical.children[0].children[0]

    assert isinstance(horizontal_content, Row)
    assert isinstance(vertical_content, Column)
    assert horizontal_content.padding == vertical_content.padding


def test_toolbar_accepts_tooltip_wrapped_button() -> None:
    wrapped = IconButton("add").modifier(tooltip(Text("Add")))
    toolbar = HorizontalFloatingToolbar([wrapped])

    row = toolbar.children[0].children[0]

    assert isinstance(row, Row)
    assert len(row.children) == 1
    assert isinstance(row.children[0], TooltipBox)
