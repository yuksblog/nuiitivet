"""Material Design 3 Vertical Menu widgets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.layout.row import Row
from nuiitivet.layout.spacer import Spacer
from nuiitivet.material.divider import Divider
from nuiitivet.material.icon import Icon
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.styles.divider_style import DividerStyle
from nuiitivet.material.styles.icon_style import IconStyle
from nuiitivet.material.styles.menu_style import MenuStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.symbols import Symbols
from nuiitivet.material.text import Text
from nuiitivet.observable import runtime
from nuiitivet.overlay.overlay_position import AnchoredOverlayPosition
from nuiitivet.rendering.elevation import resolve_shadow_params
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.theme.types import ColorBase, ColorSpec
from nuiitivet.widgets.interaction import FocusNode
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.input.pointer import PointerEvent
    from nuiitivet.material.symbols import Symbol
    from nuiitivet.overlay.overlay_handle import OverlayHandle


def _disabled_color(color: ColorSpec, disabled_color: ColorSpec, disabled: bool, *, opacity: float) -> ColorSpec:
    if disabled:
        return _with_opacity(disabled_color, opacity)
    return color


def _with_opacity(color: ColorSpec, opacity: float) -> ColorSpec:
    if isinstance(color, tuple) and len(color) == 2 and isinstance(color[1], (int, float)):
        base, alpha = color
        return (cast(ColorBase, base), float(alpha) * opacity)
    return (cast(ColorBase, color), opacity)


class MenuDivider:
    """Sentinel that renders a horizontal divider inside a Menu."""


class MenuItem(InteractiveWidget):
    """Material Design 3 menu item widget."""

    def __init__(
        self,
        label: str,
        *,
        on_click: Callable[[], None] | None = None,
        disabled: bool = False,
        leading_icon: Symbol | str | None = None,
        trailing: Symbol | str | None = None,
        height: SizingLike = None,
    ) -> None:
        """Initialize MenuItem.

        Args:
            label: Item label.
            on_click: Click callback.
            disabled: Whether this item is disabled.
            leading_icon: Optional leading icon.
            trailing: Optional trailing icon (Symbol) or trailing text (str).
            height: Optional fixed item height.
        """
        self.label = label
        self.leading_icon = leading_icon
        self.trailing = trailing
        self._menu_style: MenuStyle = MenuStyle.standard()
        self._selected = False
        self._uses_style_height = height is None
        self._leading_icon_widget: Icon | None = None
        self._label_widget: Text | None = None
        self._trailing_text_widget: Text | None = None
        self._trailing_icon_widget: Icon | None = None
        self._content_row: Row | None = None
        self._content_container: Container | None = None
        self._content_icon_size: int | None = None

        resolved_height = height if height is not None else Sizing.fixed(self._menu_style.item_height)

        super().__init__(
            child=Text(label),
            on_click=on_click,
            on_hover=self._handle_hover_change,
            on_press=self._handle_press,
            on_release=self._handle_release,
            disabled=disabled,
            state_layer_color=self._menu_style.state_layer_color,
            width=Sizing.flex(),
            height=resolved_height,
            background_color=None,
            padding=0,
            corner_radius=0,
        )
        self._build_content(self._menu_style)
        self._apply_style(self._menu_style)

    def _bind_menu_style(self, style: MenuStyle) -> None:
        self._apply_structure_style(style)
        self._menu_style = style
        self._apply_style(style)

    def _set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_style(self._menu_style)

    def _build_content(self, style: MenuStyle) -> None:
        children: list[Widget] = []
        if self.leading_icon is not None:
            self._leading_icon_widget = Icon(self.leading_icon, size=style.icon_size)
            children.append(self._leading_icon_widget)

        self._label_widget = Text(self.label, style=TextStyle(font_size=14))
        children.append(self._label_widget)
        children.append(Spacer(width=Sizing.flex()))

        trailing = self.trailing
        if trailing is not None:
            if isinstance(trailing, str):
                self._trailing_text_widget = Text(trailing, style=TextStyle(font_size=12))
                children.append(self._trailing_text_widget)
            else:
                self._trailing_icon_widget = Icon(trailing, size=style.icon_size)
                children.append(self._trailing_icon_widget)

        self._content_row = Row(
            children=children,
            width=Sizing.flex(),
            gap=style.item_spacing,
            cross_alignment="center",
        )
        self._content_container = Container(
            child=self._content_row,
            width=Sizing.flex(),
            height=Sizing.flex(),
            padding=(style.item_horizontal_padding, 0, style.item_horizontal_padding, 0),
            alignment="center-left",
        )

        self.clear_children()
        self.add_child(self._content_container)
        self._content_icon_size = int(style.icon_size)

    def _clear_content_refs(self) -> None:
        self._leading_icon_widget = None
        self._label_widget = None
        self._trailing_text_widget = None
        self._trailing_icon_widget = None
        self._content_row = None
        self._content_container = None
        self._content_icon_size = None

    def _rebuild_content(self, style: MenuStyle) -> None:
        self._clear_content_refs()
        self._build_content(style)

    def _apply_structure_style(self, style: MenuStyle) -> None:
        if self._content_container is None or self._content_row is None or self._label_widget is None:
            self._build_content(style)
            return

        if self._content_icon_size != int(style.icon_size):
            self._rebuild_content(style)
            return

        next_padding = (
            style.item_horizontal_padding,
            0,
            style.item_horizontal_padding,
            0,
        )
        if self._content_container.padding != next_padding:
            self._content_container.padding = next_padding

        if self._content_row.gap != style.item_spacing:
            self._content_row.gap = style.item_spacing

    def _apply_style(self, style: MenuStyle) -> None:
        self.state_layer_color = style.state_layer_color
        self._HOVER_OPACITY = float(style.hover_alpha)
        self._FOCUS_OPACITY = float(style.focus_alpha)
        self._PRESS_OPACITY = float(style.pressed_alpha)
        self.corner_radius = float(style.state_layer_corner_radius)

        if self._uses_style_height:
            self.height_sizing = Sizing.fixed(style.item_height)

        foreground = style.selected_foreground if self._selected else style.label_color
        icon_color = style.selected_foreground if self._selected else style.icon_color
        trailing_text_color = style.selected_foreground if self._selected else style.trailing_text_color

        # Expressive vibrant tokens use a stronger icon color while hovered/focused/pressed.
        if (
            not self._selected
            and not self.disabled
            and style.interactive_icon_color is not None
            and (self.state.hovered or self.state.focused or self.state.pressed)
        ):
            icon_color = style.interactive_icon_color

        if self.disabled and self._selected:
            foreground = _with_opacity(foreground, float(style.disabled_opacity))
            icon_color = _with_opacity(icon_color, float(style.disabled_opacity))
            trailing_text_color = _with_opacity(trailing_text_color, float(style.disabled_opacity))
        else:
            foreground = _disabled_color(
                foreground,
                style.disabled_color,
                self.disabled,
                opacity=float(style.disabled_opacity),
            )
            icon_color = _disabled_color(
                icon_color,
                style.disabled_color,
                self.disabled,
                opacity=float(style.disabled_opacity),
            )
            trailing_text_color = _disabled_color(
                trailing_text_color,
                style.disabled_color,
                self.disabled,
                opacity=float(style.disabled_opacity),
            )

        self.bgcolor = style.selected_background if self._selected else None
        if self._selected and self.disabled and style.selected_disabled_background_opacity is not None:
            self.bgcolor = _with_opacity(style.selected_background, float(style.selected_disabled_background_opacity))

        if self._leading_icon_widget is not None:
            self._leading_icon_widget._style = IconStyle(color=icon_color)

        if self._label_widget is not None:
            self._label_widget._style = TextStyle(font_size=14, color=foreground)

        if self._trailing_text_widget is not None:
            self._trailing_text_widget._style = TextStyle(font_size=12, color=trailing_text_color)

        if self._trailing_icon_widget is not None:
            self._trailing_icon_widget._style = IconStyle(color=icon_color)

        self.invalidate()

    def _handle_hover_change(self, _hovered: bool) -> None:
        self._apply_style(self._menu_style)

    def _handle_press(self, _event: PointerEvent) -> None:
        self._apply_style(self._menu_style)

    def _handle_release(self, _event: PointerEvent) -> None:
        self._apply_style(self._menu_style)

    def _handle_focus_change(self, focused: bool) -> None:
        super()._handle_focus_change(focused)
        self._apply_style(self._menu_style)


class SubMenuItem(MenuItem):
    """Material Design 3 submenu item that expands a nested menu."""

    def __init__(
        self,
        label: str,
        items: list[MenuItem | "SubMenuItem" | MenuDivider],
        *,
        leading_icon: Symbol | str | None = None,
        disabled: bool = False,
        height: SizingLike = None,
    ) -> None:
        """Initialize SubMenuItem.

        Args:
            label: Item label.
            items: Submenu entries.
            leading_icon: Optional leading icon.
            disabled: Whether this item is disabled.
            height: Optional fixed item height.
        """
        self._submenu_items = list(items)
        self._submenu_handle: OverlayHandle[object] | None = None
        self._submenu_tick: Callable[[float], None] | None = None
        self._submenu: Menu | None = None
        self._parent_dismiss: Callable[[], None] | None = None
        self._submenu_pinned = False
        self._suppress_reopen = False

        super().__init__(
            label,
            on_click=self._on_self_click,
            disabled=disabled,
            leading_icon=leading_icon,
            trailing=Symbols.chevron_right,
            height=height,
        )

    def _on_self_click(self) -> None:
        if self.disabled:
            return
        if self._submenu_pinned:
            self._submenu_pinned = False
            self._close_submenu(suppress_reopen=True)
            return
        if self._submenu_handle is not None:
            self._submenu_pinned = True
            self._suppress_reopen = False
            return
        self._submenu_pinned = True
        self._suppress_reopen = False
        self._open_submenu()

    def _is_submenu_interacting(self) -> bool:
        submenu = self._submenu
        if submenu is None:
            return False
        if submenu.state.hovered or submenu.state.focused or submenu.state.pressed:
            return True
        for item in submenu._focusable_items:
            if item.state.hovered or item.state.focused or item.state.pressed:
                return True
        return False

    def _bind_parent_dismiss(self, on_dismiss: Callable[[], None] | None) -> None:
        self._parent_dismiss = on_dismiss
        if self._submenu is not None:
            self._submenu.on_dismiss = self._chained_dismiss

    def _bind_menu_style(self, style: MenuStyle) -> None:
        super()._bind_menu_style(style)
        if self._submenu is not None:
            self._submenu.style = style
            self._submenu._rematerialize()

    def on_mount(self) -> None:
        super().on_mount()

        def _tick(_dt: float) -> None:
            self._update_submenu_visibility()

        self._submenu_tick = _tick
        runtime.clock.schedule_interval(_tick, 1.0 / 30.0)

    def _update_submenu_visibility(self) -> None:
        if self.disabled:
            self._close_submenu()
            return

        pointer_interacting = self.state.hovered or self._is_submenu_interacting()
        keyboard_focused = self.state.focused and self.should_show_focus_ring

        # Click pin should be released when pointer leaves both this item and submenu.
        if self._submenu_pinned and not pointer_interacting and not keyboard_focused:
            self._submenu_pinned = False

        if self._suppress_reopen:
            if pointer_interacting:
                return
            # Lift suppression once pointer is away so hover can open again.
            self._suppress_reopen = False
            if not self._submenu_pinned and not keyboard_focused:
                return

        if pointer_interacting or keyboard_focused or self._submenu_pinned:
            self._open_submenu()
        else:
            self._close_submenu()

    def on_unmount(self) -> None:
        if self._submenu_tick is not None:
            runtime.clock.unschedule(self._submenu_tick)
            self._submenu_tick = None
        self._close_submenu()
        super().on_unmount()

    def _ensure_submenu(self) -> Menu:
        if self._submenu is None:
            self._submenu = Menu(items=self._submenu_items, on_dismiss=self._chained_dismiss, style=self._menu_style)
        return self._submenu

    def _rect_provider(self) -> tuple[int, int, int, int] | None:
        return self.global_layout_rect

    def _open_submenu(self) -> None:
        if self._submenu_handle is not None:
            return

        if self._rect_provider() is None:
            return

        from nuiitivet.overlay.overlay import Overlay

        try:
            overlay = Overlay.root()
        except RuntimeError:
            return

        submenu = self._ensure_submenu()
        position = AnchoredOverlayPosition.anchored(
            self._rect_provider,
            alignment="top-right",
            anchor="top-left",
            offset=(0.0, 0.0),
        )
        self._submenu_handle = overlay.show_modeless(submenu, position=position)

    def _close_submenu(self, *, suppress_reopen: bool = False) -> None:
        if self._submenu_handle is not None:
            self._submenu_handle.close()
            self._submenu_handle = None
        if suppress_reopen:
            self._suppress_reopen = True
        self._submenu_pinned = False

    def _chained_dismiss(self) -> None:
        self._close_submenu(suppress_reopen=True)
        if self._parent_dismiss is not None:
            self._parent_dismiss()


class Menu(InteractiveWidget):
    """Material Design 3 vertical menu popup surface."""

    def __init__(
        self,
        items: list[MenuItem | SubMenuItem | MenuDivider],
        *,
        on_dismiss: Callable[[], None] | None = None,
        style: MenuStyle | None = None,
    ) -> None:
        """Initialize Menu.

        Args:
            items: Flat menu entries list.
            on_dismiss: Called when menu is dismissed by keyboard.
            style: Optional menu style override.
        """
        self.items = list(items)
        self.on_dismiss = on_dismiss
        self.style = style or MenuStyle.standard()
        self._focus_index = -1
        self._focusable_items: list[MenuItem] = []

        shadow_color: ColorSpec | None = None
        shadow_blur = 0.0
        shadow_offset = (0, 0)
        try:
            elevation_value = float(self.style.elevation)
        except Exception:
            elevation_value = 0.0
        if elevation_value > 0.0:
            shadow = resolve_shadow_params(elevation_value)
            shadow_color = _with_opacity(self.style.elevation_color, shadow.alpha)
            shadow_blur = shadow.blur
            shadow_offset = shadow.offset

        children = self._materialize_children()
        self._column = Column(children=children, width=Sizing.flex(), gap=0, cross_alignment="start")

        super().__init__(
            child=self._column,
            on_click=None,
            state_layer_color=self.style.state_layer_color,
            padding=(0, self.style.container_vertical_padding, 0, self.style.container_vertical_padding),
            background_color=self.style.background,
            corner_radius=self.style.corner_radius,
            shadow_blur=shadow_blur,
            shadow_color=shadow_color,
            shadow_offset=shadow_offset,
        )

        # Menu surface itself should not paint state layers.
        self._HOVER_OPACITY = 0.0
        self._PRESS_OPACITY = 0.0
        self._FOCUS_OPACITY = 0.0

    def _rematerialize(self) -> None:
        self.clear_children()
        self._column = Column(
            children=self._materialize_children(),
            width=Sizing.flex(),
            gap=0,
            cross_alignment="start",
        )
        self.add_child(self._column)
        self.invalidate()

    def _materialize_children(self) -> list[Widget]:
        out: list[Widget] = []
        self._focusable_items = []

        divider_style = DividerStyle(color=self.style.divider_color)

        for entry in self.items:
            if isinstance(entry, MenuDivider):
                out.append(
                    Container(
                        width=Sizing.flex(),
                        padding=(0, self.style.divider_vertical_padding, 0, self.style.divider_vertical_padding),
                        child=Divider(style=divider_style),
                    )
                )
                continue

            entry._bind_menu_style(self.style)
            if isinstance(entry, SubMenuItem):
                entry._bind_parent_dismiss(self.on_dismiss)
            out.append(
                Container(
                    width=Sizing.flex(),
                    padding=(self.style.item_horizontal_inset, 0, self.style.item_horizontal_inset, 0),
                    child=entry,
                )
            )
            self._focusable_items.append(entry)

        return out

    def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
        vertical = int(self.style.container_vertical_padding) * 2
        measure_max_width = int(self.style.max_width)
        if max_width is not None:
            measure_max_width = min(measure_max_width, int(max_width))

        content_width = 0
        content_height = 0

        for child in self._column.children_snapshot():
            w, h = measure_preferred_size(child, max_width=measure_max_width)
            content_width = max(content_width, int(w))
            content_height += int(h)

        resolved_width = max(int(self.style.min_width), min(int(self.style.max_width), int(content_width)))
        resolved_height = int(content_height) + vertical

        if max_width is not None:
            resolved_width = min(resolved_width, int(max_width))
        if max_height is not None:
            resolved_height = min(resolved_height, int(max_height))

        return (resolved_width, resolved_height)

    def on_key_event(self, key: str, modifiers: int = 0) -> bool:
        key_name = str(key).lower()

        if key_name == "escape":
            if self.on_dismiss is not None:
                self.on_dismiss()
            return True

        if key_name == "down":
            return self._move_focus(1)

        if key_name == "up":
            return self._move_focus(-1)

        if key_name in ("enter", "space"):
            if 0 <= self._focus_index < len(self._focusable_items):
                item = self._focusable_items[self._focus_index]
                return item.on_key_event(key_name, modifiers)
            return False

        return False

    def _move_focus(self, direction: int) -> bool:
        enabled_indices = [idx for idx, item in enumerate(self._focusable_items) if not item.disabled]
        if not enabled_indices:
            return False

        if self._focus_index not in enabled_indices:
            target_index = enabled_indices[0 if direction >= 0 else -1]
            self._set_focus_index(target_index)
            return True

        pos = enabled_indices.index(self._focus_index)
        next_pos = (pos + (1 if direction >= 0 else -1)) % len(enabled_indices)
        self._set_focus_index(enabled_indices[next_pos])
        return True

    def _set_focus_index(self, index: int) -> None:
        self._focus_index = index
        for idx, item in enumerate(self._focusable_items):
            item._set_selected(idx == index)

        focus_node = self._focusable_items[index].get_node(FocusNode)
        if isinstance(focus_node, FocusNode):
            focus_node.request_focus()


__all__ = ["Menu", "MenuDivider", "MenuItem", "SubMenuItem"]
