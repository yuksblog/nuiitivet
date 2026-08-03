"""Material Design 3 Vertical Menu widgets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Sequence, cast

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.layout.row import Row
from nuiitivet.layout.spacer import Spacer
from nuiitivet.material.divider import HorizontalDivider
from nuiitivet.material.icon import Icon
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.styles.divider_style import DividerStyle
from nuiitivet.material.styles.icon_style import IconStyle
from nuiitivet.material.styles.menu_style import MenuStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.theme.type_scale import TypeScaleToken
from nuiitivet.material.symbols import Symbols
from nuiitivet.material.text import Text
from nuiitivet.observable import runtime
from nuiitivet.overlay.overlay_position import AnchoredOverlayPosition
from nuiitivet.material.theme.elevation import md3_elevation_to_shadow
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.theme.theme import Theme
from nuiitivet.theme.types import ColorBase, ColorSpec
from nuiitivet.widgets.interaction import FocusNode, FocusScope, FocusSource, FocusTraversalPolicy
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


class _MenuTraversalPolicy(FocusTraversalPolicy):
    """Traversal policy for a Menu: the members are its enabled items.

    Tab and the arrow keys both rove them. Stepping past the last item (or before
    the first) is the boundary, and there a popup dismisses itself while an inline
    menu lets Tab escape to the next widget in the page.
    """

    def __init__(self, menu: "Menu") -> None:
        self._menu = menu

    def members(self) -> Sequence[MenuItem]:
        return [item for item in self._menu._focusable_items if not item.disabled]

    def current_index(self) -> int:
        focused = self._menu._focused_item()
        members = self.members()
        if focused is None or focused not in members:
            return -1
        return members.index(focused)

    def set_current(self, index: int) -> None:
        members = self.members()
        if 0 <= index < len(members):
            self._menu._focus_item(members[index])

    def on_boundary(self, direction: int) -> bool:
        # A popup menu is left by dismissing it. An inline menu stays put and is
        # a single Tab stop in the page, so Tab escapes to the next widget.
        if not self._menu._is_popup():
            return False
        self._menu._dismiss()
        return True


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
    ) -> None:
        """Initialize MenuItem.

        The item height is MD3-fixed (list-item token), so it is not a
        constructor parameter; customize it via ``MenuStyle.item_height``
        (SIZE_POLICY: MD3 fixes the axis -> style only).

        Args:
            label: Item label.
            on_click: Click callback.
            disabled: Whether this item is disabled.
            leading_icon: Optional leading icon.
            trailing: Optional trailing icon (Symbol) or trailing text (str).
        """
        self.label = label
        self.leading_icon = leading_icon
        self.trailing = trailing
        self._menu_style: MenuStyle = MenuStyle.standard()
        self._owner_menu: Menu | None = None
        self._selected = False
        self._leading_icon_widget: Icon | None = None
        self._label_widget: Text | None = None
        self._trailing_text_widget: Text | None = None
        self._trailing_icon_widget: Icon | None = None
        self._content_row: Row | None = None
        self._content_container: Container | None = None
        self._content_icon_size: int | None = None

        resolved_height = Sizing.fixed(self._menu_style.item_height)

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
            # The enclosing Menu's FocusScope moves focus between the items; the
            # global Tab sequence must not stop on them (WAI-ARIA menu pattern).
            traversable=False,
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

        self._label_widget = Text(self.label, type_scale=TypeScaleToken.from_size(14))
        children.append(self._label_widget)
        children.append(Spacer(width=Sizing.flex()))

        trailing = self.trailing
        if trailing is not None:
            if isinstance(trailing, str):
                self._trailing_text_widget = Text(trailing, type_scale=TypeScaleToken.from_size(12))
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
            self._label_widget._style = TextStyle(color=foreground)

        if self._trailing_text_widget is not None:
            self._trailing_text_widget._style = TextStyle(color=trailing_text_color)

        if self._trailing_icon_widget is not None:
            self._trailing_icon_widget._style = IconStyle(color=icon_color)

        self.invalidate()

    def on_mount(self) -> None:
        super().on_mount()
        if self._owner_menu is not None:
            self._owner_menu._item_mounted(self)

    def _get_active_state_layer_opacity(self) -> float:
        """Paint the focus state layer for the keyboard-focused item.

        The base class only layers hover/press; a menu roves with the arrow keys,
        so the focused item needs the MD3 focus layer to show where it is.
        """
        opacity = super()._get_active_state_layer_opacity()
        if opacity <= 0.0 and self.should_show_focus_ring:
            return self._FOCUS_OPACITY
        return opacity

    def _handle_hover_change(self, _hovered: bool) -> None:
        self._apply_style(self._menu_style)

    def _handle_press(self, _event: PointerEvent) -> None:
        self._apply_style(self._menu_style)

    def _handle_release(self, _event: PointerEvent) -> None:
        self._apply_style(self._menu_style)

    def _on_focused(self, focused: bool, source: FocusSource) -> None:
        # Focus can also arrive from a click, so tell the menu rather than let its
        # roving index go stale.
        if focused and self._owner_menu is not None:
            self._owner_menu._on_item_focused(self)
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
    ) -> None:
        """Initialize SubMenuItem.

        Args:
            label: Item label.
            items: Submenu entries.
            leading_icon: Optional leading icon.
            disabled: Whether this item is disabled.
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
            self._submenu._adopt_style(style)
            self._submenu._apply_menu_style(style)

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
            # A submenu also opens on hover, which must not steal the keyboard
            # focus: it is focused only when the user walks into it with Right.
            self._submenu = Menu(
                items=self._submenu_items,
                on_dismiss=self._chained_dismiss,
                style=self._menu_style,
                autofocus=False,
                parent_item=self,
            )
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
    """Material Design 3 vertical menu popup surface.

    The menu is a focus traversal group. Opening a popup moves the focus onto the
    menu surface, with no item current — nothing is highlighted, as in a desktop
    menu — unless it was opened from the keyboard, which focuses the first enabled
    item. Up/Down rove the items (wrapping), Tab/Shift+Tab rove them too (without
    wrapping) and dismiss the popup once they step past the end, Right/Left walk
    into and out of a submenu, and Escape dismisses.

    An inline menu (one placed in the page rather than shown as an overlay) is a
    single Tab stop instead: Tab enters it, roves it, and leaves it for the next
    widget rather than dismissing anything.
    """

    def __init__(
        self,
        items: list[MenuItem | SubMenuItem | MenuDivider],
        *,
        on_dismiss: Callable[[], None] | None = None,
        style: MenuStyle | None = None,
        autofocus: bool = True,
        parent_item: "SubMenuItem | None" = None,
    ) -> None:
        """Initialize Menu.

        Args:
            items: Flat menu entries list.
            on_dismiss: Called when menu is dismissed by keyboard.
            style: Optional menu style override.
            autofocus: Whether opening the menu focuses its first enabled item.
            parent_item: The SubMenuItem this menu expands from, if it is a submenu.
        """
        self.items = list(items)
        self.on_dismiss = on_dismiss
        # Held in a local for everything below ``super().__init__()``: reads that
        # run before the widget is attached must not go through an accessor that
        # could reach for the theme, which is not resolvable yet. The preset is
        # what ``MenuStyle.from_theme`` falls back to, so an unthemed app sees
        # no change; a themed one adopts its style on the first measure.
        effective_style = style or MenuStyle.preset()
        #: The style the caller passed, or ``None`` to follow the theme.
        self._user_style: MenuStyle | None = style
        self._applied_style: MenuStyle = effective_style
        self._autofocus = bool(autofocus)
        self._autofocus_pending = False
        self._parent_item = parent_item
        self._focus_index = -1
        self._focusable_items: list[MenuItem] = []

        _shadow = md3_elevation_to_shadow(effective_style.elevation)

        children = self._materialize_children(effective_style)
        self._column = Column(children=children, width=Sizing.flex(), gap=0, cross_alignment="start")

        super().__init__(
            child=self._column,
            on_click=None,
            state_layer_color=effective_style.state_layer_color,
            padding=(
                0,
                effective_style.container_vertical_padding,
                0,
                effective_style.container_vertical_padding,
            ),
            background_color=effective_style.background,
            corner_radius=effective_style.corner_radius,
            shadow_blur=_shadow.sigma,
            shadow_color=_shadow.color,
            shadow_offset=_shadow.offset,
            # The menu is one group, not a row of stops: Tab neither lands on the
            # surface nor on the items, it leaves the menu (see the scope below).
            traversable=False,
        )

        # Tab roves the items like everywhere else in the framework: it is the key
        # the user presses to be given the focus, so the first Tab must land on an
        # item, not close the menu. Only stepping past the last item is a boundary
        # (see _MenuTraversalPolicy.on_boundary). The arrow keys wrap; Tab does not.
        self._focus_scope = FocusScope(_MenuTraversalPolicy(self))
        self.add_node(self._focus_scope)

        # Menu surface itself should not paint state layers.
        self._HOVER_OPACITY = 0.0
        self._PRESS_OPACITY = 0.0
        self._FOCUS_OPACITY = 0.0

    def on_mount(self) -> None:
        super().on_mount()
        # A popup is entered by opening it, so it is no Tab stop at all. An inline
        # menu is part of the page, and WAI-ARIA makes it a single stop: Tab lands
        # on the menu, the scope focuses an item, and the arrows take over.
        node = self.get_node(FocusNode)
        if isinstance(node, FocusNode):
            node.traversable = not self._is_popup()

        # Opening a popup moves the focus into the menu, but onto the surface: no
        # item is current yet. Arrow keys, Escape and Tab all reach the menu from
        # there, while Enter has nothing to activate — which is what the user sees,
        # since nothing is highlighted. A keyboard-opened menu goes on to focus its
        # first item in _item_mounted.
        if self._autofocus and self._is_popup() and not self._holds_focus():
            self._focus_surface()

    def on_unmount(self) -> None:
        # A closed menu must not keep the focus: the instance is reused when it is
        # shown again (light_dismiss holds on to it), and a stale focused item would
        # both hold the app's focus and suppress the focus-on-open.
        if self._holds_focus():
            self._clear_focus()
        super().on_unmount()

    @property
    def should_show_focus_ring(self) -> bool:
        """Never ring the surface: it holds the focus, but the items show where it is."""
        return False

    # --- Theme integration ----------------------------------------------------

    @property
    def style(self) -> MenuStyle:
        """Return the menu style currently in effect, pulled from the theme.

        A menu has no ``build()``, so it reads the theme where the style is
        consumed -- :meth:`preferred_size`. The read registers a dependency, so
        a theme change re-measures the menu and lands back here with the new
        value. The container visuals and the items' styles are derived from it
        rather than re-derived on every read, so they are re-applied whenever
        the resolved style has moved. See ``docs/design/THEME_CONSUMPTION.md``.
        """
        if self._user_style is not None:
            resolved = self._user_style
        else:
            resolved = MenuStyle.from_theme(Theme.of(self))
        if resolved != self._applied_style:
            self._apply_menu_style(resolved)
        return resolved

    def _adopt_style(self, style: MenuStyle) -> None:
        """Take ``style`` as this menu's explicit style.

        A submenu is styled by the menu it hangs off rather than by the theme
        directly: the parent has already resolved one, and the two surfaces
        must match.
        """
        self._user_style = style

    def _apply_menu_style(self, style: MenuStyle) -> None:
        """Push ``style`` onto the surface and rebuild the items with it."""
        # Recorded first: rebuilding the items reads ``self.style`` again, and
        # that read must not re-enter this method.
        self._applied_style = style

        shadow = md3_elevation_to_shadow(style.elevation)
        self.state_layer_color = style.state_layer_color
        self.padding = (0, style.container_vertical_padding, 0, style.container_vertical_padding)
        self.bgcolor = style.background
        self.corner_radius = style.corner_radius
        self.shadow_blur = shadow.sigma
        self.shadow_color = shadow.color
        self.shadow_offset = shadow.offset
        self._rematerialize()

    def _focus_surface(self) -> None:
        """Move the focus into the menu without making any item current."""
        node = self.get_node(FocusNode)
        if isinstance(node, FocusNode):
            self._focus_index = -1
            node.request_focus(self._open_focus_source())

    def _clear_focus(self) -> None:
        """Blur whatever this menu has focused and forget the roving position."""
        app = getattr(self, "_app", None)
        if app is not None:
            app.request_focus(None)
        else:
            nodes = [self.get_node(FocusNode)] + [item.get_node(FocusNode) for item in self._focusable_items]
            for node in nodes:
                if isinstance(node, FocusNode):
                    node._set_focused(False)

        self._focus_index = -1

    def _is_popup(self) -> bool:
        """True when the menu is shown as an overlay entry rather than placed inline.

        Only a popup takes focus when it appears: an inline menu is just part of
        the page, and stealing focus at startup would be wrong.
        """
        from nuiitivet.overlay.overlay import Overlay

        return self.find_ancestor(Overlay) is not None

    def focus_first_item(self) -> bool:
        """Focus the first enabled item.

        Returns False if the menu has no enabled item, or if it is not mounted
        yet: a widget's ``on_mount`` runs before its children's, so in that case
        the request is latched and :meth:`_item_mounted` completes it.
        """
        item = self._first_enabled_item()
        if item is None:
            return False
        if getattr(item, "_app", None) is None:
            self._autofocus_pending = True
            return False

        self._autofocus_pending = False
        self._focus_item(item)
        return True

    def _first_enabled_item(self) -> MenuItem | None:
        for item in self._focusable_items:
            if not item.disabled:
                return item
        return None

    def _holds_item_focus(self) -> bool:
        """True if one of this menu's items holds the focus, or a submenu of one does."""
        for item in self._focusable_items:
            if item.state.focused:
                return True
            if isinstance(item, SubMenuItem) and item._submenu is not None and item._submenu._holds_item_focus():
                return True
        return False

    def _holds_focus(self) -> bool:
        """True if the focus is anywhere in this menu — the surface included."""
        return self.state.focused or self._holds_item_focus()

    def _item_mounted(self, item: MenuItem) -> None:
        """Make the first item current when the menu was opened from the keyboard.

        Opening with the pointer leaves the focus on the surface (see ``on_mount``):
        nothing is highlighted, exactly as in a desktop menu, and the arrow keys pick
        the first item from there. Recomposition re-mounts the items while the menu
        is already open, hence the check that no item has the focus yet — a remount
        must not yank focus back from a submenu the user walked into.
        """
        if item is not self._first_enabled_item():
            return
        if self._holds_item_focus():
            return

        if self._autofocus_pending:
            # An explicit request (walking into a submenu with Right) that arrived
            # before the items existed.
            self._autofocus_pending = False
            self._focus_item(item)
            return

        if self._autofocus and self._is_popup() and self._open_focus_source() is FocusSource.KEYBOARD:
            self._focus_item(item)

    def _rematerialize(self) -> None:
        self.clear_children()
        self._column = Column(
            children=self._materialize_children(self._applied_style),
            width=Sizing.flex(),
            gap=0,
            cross_alignment="start",
        )
        self.add_child(self._column)
        self.invalidate()

    def _materialize_children(self, style: MenuStyle) -> list[Widget]:
        """Build the entry widgets for ``style``.

        Takes the style rather than reading :attr:`style`: ``__init__`` calls
        this before ``super().__init__()``, where the theme cannot be resolved
        at all.
        """
        out: list[Widget] = []
        self._focusable_items = []

        divider_style = DividerStyle(color=style.divider_color)

        for entry in self.items:
            if isinstance(entry, MenuDivider):
                out.append(
                    Container(
                        width=Sizing.flex(),
                        padding=(0, style.divider_vertical_padding, 0, style.divider_vertical_padding),
                        child=HorizontalDivider(style=divider_style),
                    )
                )
                continue

            entry._bind_menu_style(style)
            entry._owner_menu = self
            if isinstance(entry, SubMenuItem):
                entry._bind_parent_dismiss(self.on_dismiss)
            out.append(
                Container(
                    width=Sizing.flex(),
                    padding=(style.item_horizontal_inset, 0, style.item_horizontal_inset, 0),
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

    def on_key_event(self, key: str, modifier_keys: int = 0) -> bool:
        key_name = str(key).lower()

        if key_name == "escape":
            self._dismiss()
            return True

        if key_name == "down":
            return self._move_focus(1)

        if key_name == "up":
            return self._move_focus(-1)

        if key_name == "right":
            return self._enter_submenu()

        if key_name == "left":
            return self._leave_submenu()

        if key_name in ("enter", "space"):
            item = self._focused_item()
            if item is not None:
                return item.on_key_event(key_name, modifier_keys)
            return False

        return False

    def _dismiss(self) -> None:
        """Dismiss the menu (Escape, or Tab leaving the scope)."""
        if self.on_dismiss is not None:
            self.on_dismiss()

    def _move_focus(self, direction: int) -> bool:
        """Rove one enabled item up (-1) or down (+1), wrapping at the ends."""
        return self._focus_scope.move(1 if direction >= 0 else -1, wrap=True)

    def _enter_submenu(self) -> bool:
        """Open the focused SubMenuItem's submenu and focus its first item."""
        item = self._focused_item()
        if not isinstance(item, SubMenuItem) or item.disabled:
            return False

        submenu = item._ensure_submenu()
        item._submenu_pinned = True
        item._suppress_reopen = False
        item._open_submenu()
        # If hover already opened the submenu it is mounted and this focuses it
        # now; otherwise the request is latched until its items mount.
        submenu.focus_first_item()
        return True

    def _leave_submenu(self) -> bool:
        """Close this submenu and return focus to the SubMenuItem that opened it."""
        item = self._parent_item
        if item is None:
            return False

        owner = item._owner_menu
        if owner is not None:
            owner._focus_item(item)
        item._close_submenu(suppress_reopen=True)
        return True

    def _focused_item(self) -> MenuItem | None:
        """Return the item that currently holds focus, if any."""
        if 0 <= self._focus_index < len(self._focusable_items):
            return self._focusable_items[self._focus_index]
        return None

    def _focus_item(self, item: MenuItem) -> None:
        """Focus ``item`` and make it the menu's current row.

        Items are only ever made current by the keyboard — the arrow keys, Tab into
        an inline menu, or opening the menu from the keyboard — so the focus is
        keyboard-driven by construction and the item shows a focus ring.
        """
        self._set_focus_index(self._focusable_items.index(item))

    def _on_item_focused(self, item: MenuItem) -> None:
        """Sync the roving index when an item gains focus on its own (e.g. a click).

        Only the index: re-requesting the focus here would announce a keyboard
        source and ring an item the user just clicked.
        """
        self._focus_index = self._focusable_items.index(item)

    def _open_focus_source(self) -> FocusSource:
        """How the user opened the menu, as far as the app can tell.

        Focus-on-open must not make a mouse-opened menu come up with its first item
        wearing a keyboard focus ring. The item still takes focus — the arrow keys
        need somewhere to start — it just does not look keyboard-driven until the
        user actually drives it with the keyboard.
        """
        app = getattr(self, "_app", None)
        source = getattr(app, "_last_input_source", None)
        return source if isinstance(source, FocusSource) else FocusSource.KEYBOARD

    def _set_focus_index(self, index: int) -> None:
        # Roving is focus, not selection: the focused item paints the MD3 focus
        # state layer (see MenuItem._get_active_state_layer_opacity), while
        # ``selected`` stays reserved for a genuinely selected entry.
        self._focus_index = index

        focus_node = self._focusable_items[index].get_node(FocusNode)
        if isinstance(focus_node, FocusNode):
            focus_node.request_focus(FocusSource.KEYBOARD)


__all__ = ["Menu", "MenuDivider", "MenuItem", "SubMenuItem"]
