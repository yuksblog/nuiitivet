"""Tests for Menu widgets and MenuStyle."""

from __future__ import annotations

from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material import Menu, MenuDivider, MenuItem, SubMenuItem
from nuiitivet.material.icon import Icon
from nuiitivet.material.symbols import Symbols
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from nuiitivet.overlay.overlay_handle import OverlayHandle
from nuiitivet.material.styles.menu_style import MenuStyle
from nuiitivet.material.text import Text
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.rendering.elevation import Elevation
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.interaction import FocusNode


def test_menu_style_defaults() -> None:
    style = MenuStyle.standard()
    assert style.background == ColorRole.SURFACE
    assert style.corner_radius == 16
    assert style.item_horizontal_inset == 4
    assert style.state_layer_corner_radius == 8
    assert style.elevation == 3.0
    assert style.elevation_color == ColorRole.SHADOW
    assert style.min_width == 112
    assert style.max_width == 280
    assert style.item_height == 44
    assert style.icon_size == 20
    assert style.pressed_alpha == 0.1


def test_menu_style_vibrant() -> None:
    style = MenuStyle.vibrant()
    assert style.background == ColorRole.TERTIARY_CONTAINER
    assert style.label_color == ColorRole.ON_TERTIARY_CONTAINER
    assert style.selected_background == ColorRole.TERTIARY
    assert style.selected_foreground == ColorRole.ON_TERTIARY


def test_menu_style_copy_with() -> None:
    style = MenuStyle().copy_with(min_width=144)
    assert style.min_width == 144
    assert style.max_width == 280


def test_menu_item_layout_with_trailing_text() -> None:
    item = MenuItem("Save As...", trailing="Shift+Ctrl+S")
    container = item.children_snapshot()[0]
    assert isinstance(container, Container)

    row = container.children_snapshot()[0]
    assert isinstance(row, Row)
    children = row.children_snapshot()

    assert isinstance(children[0], Text)
    assert isinstance(children[-1], Text)


def test_menu_item_layout_with_icon_trailing() -> None:
    item = MenuItem("Open", trailing=Symbols.chevron_right)
    container = item.children_snapshot()[0]
    assert isinstance(container, Container)
    row = container.children_snapshot()[0]
    children = row.children_snapshot()
    assert any(isinstance(child, Icon) for child in children)


def test_menu_materializes_divider_entries() -> None:
    menu = Menu(items=[MenuItem("Cut"), MenuDivider(), MenuItem("Paste")])
    column = menu.children_snapshot()[0]
    children = column.children_snapshot()
    assert len(children) == 3
    assert isinstance(children[1], Container)
    assert isinstance(children[0], Container)
    assert children[0].padding == (4, 0, 4, 0)


def test_menu_keyboard_navigation_and_activation() -> None:
    clicked: list[str] = []

    menu = Menu(
        items=[
            MenuItem("A", on_click=lambda: clicked.append("A")),
            MenuItem("B", disabled=True, on_click=lambda: clicked.append("B")),
            MenuItem("C", on_click=lambda: clicked.append("C")),
        ]
    )

    assert menu.on_key_event("down") is True
    assert menu.on_key_event("enter") is True
    assert clicked == ["A"]

    assert menu.on_key_event("down") is True
    assert menu.on_key_event("enter") is True
    assert clicked == ["A", "C"]


def test_menu_escape_calls_on_dismiss() -> None:
    dismissed = False

    def _dismiss() -> None:
        nonlocal dismissed
        dismissed = True

    menu = Menu(items=[MenuItem("A")], on_dismiss=_dismiss)
    assert menu.on_key_event("escape") is True
    assert dismissed is True


def test_submenu_item_has_focus_node() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    assert item.get_node(FocusNode) is not None


def test_menu_importable_from_material() -> None:
    from nuiitivet.material import Menu as ImportedMenu
    from nuiitivet.material import MenuDivider as ImportedMenuDivider
    from nuiitivet.material import MenuItem as ImportedMenuItem
    from nuiitivet.material import SubMenuItem as ImportedSubMenuItem

    assert ImportedMenu is Menu
    assert ImportedMenuItem is MenuItem
    assert ImportedSubMenuItem is SubMenuItem
    assert ImportedMenuDivider is MenuDivider


def test_menu_item_uses_style_disabled_color() -> None:
    item = MenuItem("Disabled", disabled=True)
    style = MenuStyle().copy_with(disabled_color=ColorRole.ERROR)
    item._bind_menu_style(style)

    container = item.children_snapshot()[0]
    row = container.children_snapshot()[0]
    label = row.children_snapshot()[0]
    assert isinstance(label, Text)
    assert label.style.color == (ColorRole.ERROR, 0.38)


def test_menu_item_selected_disabled_uses_selected_foreground_opacity() -> None:
    item = MenuItem("Selected", disabled=True)
    style = MenuStyle.standard()
    item._bind_menu_style(style)
    item._set_selected(True)

    container = item.children_snapshot()[0]
    row = container.children_snapshot()[0]
    label = row.children_snapshot()[0]
    assert isinstance(label, Text)
    assert label.style.color == (style.selected_foreground, style.disabled_opacity)
    assert item.bgcolor == (style.selected_background, style.selected_disabled_background_opacity)


def test_menu_item_vibrant_hover_uses_interactive_icon_color() -> None:
    item = MenuItem("Vibrant", leading_icon=Symbols.close)
    style = MenuStyle.vibrant()
    item.state.hovered = True
    item._bind_menu_style(style)

    container = item.children_snapshot()[0]
    row = container.children_snapshot()[0]
    icon = row.children_snapshot()[0]
    assert isinstance(icon, Icon)
    assert icon.style.color == style.interactive_icon_color


def test_menu_item_hover_callback_updates_interactive_icon_color() -> None:
    item = MenuItem("Vibrant", leading_icon=Symbols.close)
    style = MenuStyle.vibrant()
    item._bind_menu_style(style)

    item.state.hovered = True
    item._handle_hover_change(True)

    container = item.children_snapshot()[0]
    row = container.children_snapshot()[0]
    icon = row.children_snapshot()[0]
    assert isinstance(icon, Icon)
    assert icon.style.color == style.interactive_icon_color


def test_menu_item_hover_does_not_replace_content_container() -> None:
    item = MenuItem("Vibrant", leading_icon=Symbols.close)
    style = MenuStyle.vibrant()
    item._bind_menu_style(style)

    before = item.children_snapshot()[0]
    item.state.hovered = True
    item._handle_hover_change(True)
    after = item.children_snapshot()[0]

    assert before is after


def test_menu_item_style_change_with_icon_size_rebuilds_content_container() -> None:
    item = MenuItem("Open", leading_icon=Symbols.close)
    before = item.children_snapshot()[0]

    style = MenuStyle.standard().copy_with(icon_size=28)
    item._bind_menu_style(style)
    after = item.children_snapshot()[0]

    assert before is not after


def test_menu_item_uses_style_item_height_when_not_explicit() -> None:
    item = MenuItem("Height")
    style = MenuStyle().copy_with(item_height=56)
    item._bind_menu_style(style)

    assert item.height_sizing == Sizing.fixed(56)


def test_menu_item_uses_state_layer_corner_radius() -> None:
    item = MenuItem("Radius")
    style = MenuStyle().copy_with(state_layer_corner_radius=10)
    item._bind_menu_style(style)

    assert item.corner_radius == 10.0


def test_menu_uses_style_elevation() -> None:
    style = MenuStyle().copy_with(elevation=6.0, elevation_color=ColorRole.SCRIM)
    menu = Menu(items=[MenuItem("One")], style=style)
    elev = Elevation.from_level(6.0)

    assert menu.shadow_blur == elev.blur
    assert menu.shadow_offset == elev.offset
    assert menu.shadow_color == (ColorRole.SCRIM, elev.alpha)


def test_menu_preferred_size_passes_effective_max_width_to_measurement() -> None:
    class _ProbeContainer(Container):
        def __init__(self) -> None:
            super().__init__(child=Text("probe"))
            self.last_constraints: tuple[int | None, int | None] | None = None

        def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
            self.last_constraints = (max_width, max_height)
            return (10, 10)

    probe = _ProbeContainer()
    menu = Menu(items=[MenuItem("One")])
    menu._column = Row(children=[probe])  # type: ignore[assignment]

    menu.preferred_size(max_width=120)

    assert probe.last_constraints is not None
    assert probe.last_constraints[0] == 120


def test_submenu_item_click_pins_submenu() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    opened = False

    def _open() -> None:
        nonlocal opened
        opened = True

    item._open_submenu = _open  # type: ignore[method-assign]
    item._on_self_click()

    assert opened is True
    assert item._submenu_pinned is True


def test_submenu_item_second_click_unpins_and_closes() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    closes = 0

    def _close(*, suppress_reopen: bool = False) -> None:
        nonlocal closes
        closes += 1
        item._submenu_pinned = False
        item._suppress_reopen = suppress_reopen

    item._submenu_pinned = True
    item._close_submenu = _close  # type: ignore[method-assign]
    item._on_self_click()

    assert closes == 1
    assert item._submenu_pinned is False


def test_submenu_item_second_click_suppresses_reopen() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    item._submenu_pinned = True
    item.state.hovered = True

    item._on_self_click()

    assert item._submenu_pinned is False
    assert item._suppress_reopen is True


def test_submenu_chained_dismiss_suppresses_reopen() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])

    item._chained_dismiss()

    assert item._suppress_reopen is True


def test_submenu_item_click_pins_when_handle_exists() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    closes = 0

    class _Handle:
        def close(self) -> None:
            nonlocal closes
            closes += 1

    item._submenu_handle = cast("OverlayHandle[object]", _Handle())
    item._submenu_pinned = False

    item._on_self_click()

    assert closes == 0
    assert item._submenu_handle is not None
    assert item._submenu_pinned is True


def test_submenu_suppress_reopen_clears_without_pointer_even_if_focused_from_pointer() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    opened = False

    def _open() -> None:
        nonlocal opened
        opened = True

    item._open_submenu = _open  # type: ignore[method-assign]
    item._suppress_reopen = True
    item.state.focused = True
    item._focus_from_pointer = True
    item.state.hovered = False

    item._update_submenu_visibility()

    assert item._suppress_reopen is False
    assert opened is False


def test_submenu_hover_opens_again_after_suppress_cleared() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    opens = 0

    def _open() -> None:
        nonlocal opens
        opens += 1

    item._open_submenu = _open  # type: ignore[method-assign]
    item._suppress_reopen = True
    item.state.focused = True
    item._focus_from_pointer = True

    item.state.hovered = False
    item._update_submenu_visibility()
    item.state.hovered = True
    item._update_submenu_visibility()

    assert opens == 1


def test_submenu_pin_released_when_pointer_leaves() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    closes = 0

    class _Handle:
        def close(self) -> None:
            nonlocal closes
            closes += 1

    item._submenu_handle = cast("OverlayHandle[object]", _Handle())
    item._submenu_pinned = True
    item.state.hovered = False
    item.state.focused = False
    item._focus_from_pointer = True

    item._update_submenu_visibility()

    assert closes == 1
    assert item._submenu_pinned is False


def test_submenu_item_detects_submenu_child_interaction() -> None:
    item = SubMenuItem("Export", items=[MenuItem("PNG")])
    submenu = Menu(items=[MenuItem("PNG")])
    submenu._focusable_items[0].state.hovered = True
    item._submenu = submenu

    assert item._is_submenu_interacting() is True
