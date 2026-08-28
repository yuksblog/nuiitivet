"""The in-app menu bar widget (Windows/Linux rendering of the menu model).

Internal: apps register a model via ``App(menu=...)`` and this widget is
created by the active slot (see ``slots.py``). Popups reuse the Material
``Menu`` machinery through a thin adapter, but their colors come from the
menu bar's own palette so a non-Material design system does not get
Material-colored popups (``docs/design/MENU_BAR.md``, Section 8.4).

This module imports ``nuiitivet.material``, which the rest of the package
must not: ``nuiitivet.runtime.app`` imports the package, and only the slots'
deferred import of this module (at first build) keeps that acyclic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

from nuiitivet.input.shortcut import ShortcutBinding, ShortcutScope
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.menu import Menu, MenuDivider, MenuItem, SubMenuItem
from nuiitivet.material.styles.menu_style import MenuStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.symbols import Symbols
from nuiitivet.material.text import Text
from nuiitivet.modifiers.key_shortcut import KeyShortcutModifier
from nuiitivet.observable import ComputedObservable, ObservableBase
from nuiitivet.overlay.overlay_position import OverlayPosition
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.theme.theme import Theme
from nuiitivet.theme.type_scale import TypeScaleToken
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box

from .controller import MenuBarController
from .model import MenuBar, MenuBarItem
from .style import MenuBarStyle
from .theme_data import MenuBarThemeData

if TYPE_CHECKING:
    from nuiitivet.overlay.overlay_handle import OverlayHandle

logger = logging.getLogger(__name__)


def _inverted(enabled: "bool | ObservableBase[bool]") -> "bool | ObservableBase[bool]":
    """``disabled`` from ``enabled``: negate a bool or derive from an Observable."""
    if isinstance(enabled, ObservableBase):
        return ComputedObservable(lambda: not bool(enabled.value))
    return not bool(enabled)


class MenuBarWidget(ComposableWidget):
    """Renders a :class:`~nuiitivet.menubar.MenuBar` model as a horizontal bar.

    Created by the active menu bar slot; not part of the public API. Owns the
    open-popup state, the popup adapter, and the model's shortcut bindings
    (registered app-wide with ``ShortcutScope.MOUNT`` for as long as this bar
    is mounted).
    """

    def __init__(self, model: MenuBar) -> None:
        super().__init__()
        self._model = model
        self._style = model.style or MenuBarStyle()
        self._palette = MenuBarThemeData()
        self._top_widgets: Dict[int, "_MenuBarTopItem"] = {}
        self._open_index: Optional[int] = None
        self._handle: Optional["OverlayHandle[object]"] = None
        self._popup: Optional[Widget] = None
        self._open_subscriptions: List[object] = []

    # ---- Build -------------------------------------------------------------

    def build(self) -> Widget:
        # Reading the theme here registers this widget as a theme reader, so a
        # theme change rebuilds the bar with the new palette; the ColorSpec
        # tokens passed to children resolve at paint time for light/dark.
        theme = Theme.of(self)
        self._palette = self._style.merged_palette(theme.extension(MenuBarThemeData))

        self._top_widgets = {}
        children: List[Widget] = []
        for index, item in enumerate(self._model.items):
            if item.is_separator:
                continue
            top = _MenuBarTopItem(self, index, item, self._palette, self._style)
            self._top_widgets[index] = top
            children.append(top)

        row = Row(
            children=children,
            gap=self._style.item_gap,
            cross_alignment="center",
            height=Sizing.weight(),
        )
        pad = self._style.bar_horizontal_padding
        content = Container(
            child=row,
            width=Sizing.weight(),
            height=Sizing.weight(),
            padding=(pad, 0, pad, 0),
            alignment="center-left",
        )
        bar: Widget = Box(
            child=content,
            width=Sizing.weight(),
            height=Sizing.fixed(self._style.bar_height),
            background_color=self._palette.bar_background,
        )

        for binding in self._collect_bindings(self._model.items):
            bar = KeyShortcutModifier(binding).apply(bar)
        return bar

    def _collect_bindings(self, items: Sequence[MenuBarItem]) -> List[ShortcutBinding]:
        bindings: List[ShortcutBinding] = []
        for item in items:
            if item.is_separator:
                continue
            if item.submenu is not None:
                bindings.extend(self._collect_bindings(item.submenu))
            elif item.shortcut is not None:
                bindings.append(
                    ShortcutBinding(item.shortcut, self._make_trigger(item), ShortcutScope.MOUNT)
                )
        return bindings

    def _make_trigger(self, item: MenuBarItem):
        def fire() -> None:
            if item.resolved_enabled():
                self.activate(item)

        return fire

    def on_unmount(self) -> None:
        self.close_menu()
        super().on_unmount()

    # ---- Activation ----------------------------------------------------------

    def activate(self, item: MenuBarItem) -> None:
        """Activate an action item: close the menu, then run its command.

        The command itself (checked toggling, standard-item intents,
        ``on_select``) is the controller's shared activation path.
        """
        self.close_menu()
        controller = self._controller()
        if controller is not None:
            controller.activate(item)

    def _controller(self) -> Optional[MenuBarController]:
        from nuiitivet.widgeting.context_lookup import find_app

        app = find_app(self)
        return getattr(app, "_menubar_controller", None)

    # ---- Popup management ------------------------------------------------------

    def toggle_menu(self, index: int, *, via_keyboard: bool = False) -> None:
        if self._open_index == index:
            self.close_menu()
        else:
            self.open_menu(index, via_keyboard=via_keyboard)

    def open_menu(self, index: int, *, via_keyboard: bool = False) -> None:
        """Open the popup for a top-level item (or activate an action item)."""
        item = self._model.items[index]
        if item.is_separator or not item.resolved_enabled():
            return
        if item.submenu is None:
            self.activate(item)
            return

        self.close_menu()

        from nuiitivet.overlay.overlay import Overlay

        try:
            overlay = Overlay.of(self, root=True)
        except RuntimeError:
            return

        top = self._top_widgets.get(index)
        if top is None or top.global_layout_rect is None:
            return

        popup = _MenuBarPopup(self, self._build_popup_entries(item.submenu))
        position = OverlayPosition.anchored(
            lambda: top.global_layout_rect,
            target_anchor="bottom-left",
            content_anchor="top-left",
            offset=(0.0, 0.0),
        )
        self._handle = overlay.show(
            popup, passthrough=False, dismiss_on_outside_tap=True, position=position
        )
        self._popup = popup
        self._open_index = index
        top.set_open(True)
        if via_keyboard:
            popup.focus_first_item()
        self._subscribe_open_items(item.submenu)

    def close_menu(self) -> None:
        """Close the open popup, if any, and clear the bar's open state."""
        handle, self._handle = self._handle, None
        self._popup = None
        if self._open_index is not None:
            top = self._top_widgets.get(self._open_index)
            if top is not None:
                top.set_open(False)
            self._open_index = None
        self._dispose_open_subscriptions()
        if handle is not None:
            handle.close()

    def popup_gone(self, popup: Widget) -> None:
        """The popup left the tree: sync the bar state on a real dismissal.

        The overlay restacks its layers whenever another entry opens or closes
        (a submenu opening, the previous menu closing), remounting the live
        entries on the way — so an unmount alone is not a dismissal. Only an
        entry whose result is settled (``handle.done()``: the outside tap) has
        actually closed under us.
        """
        if self._popup is popup and self._handle is not None and self._handle.done():
            self._handle = None
            self.close_menu()

    def switch(self, direction: int) -> bool:
        """Open the adjacent top-level menu (popup Left/Right), wrapping."""
        if self._open_index is None:
            return False
        candidates = [
            index
            for index, item in enumerate(self._model.items)
            if item.submenu is not None and item.resolved_enabled()
        ]
        if len(candidates) < 2 or self._open_index not in candidates:
            return False
        at = candidates.index(self._open_index)
        self.open_menu(candidates[(at + direction) % len(candidates)], via_keyboard=True)
        return True

    def top_item_hovered(self, index: int) -> None:
        """Hover-switch: while a menu is open, hovering another title opens it."""
        if self._open_index is not None and self._open_index != index:
            item = self._model.items[index]
            if item.submenu is not None and item.resolved_enabled():
                self.open_menu(index)

    # ---- Live updates while open -------------------------------------------------

    def _subscribe_open_items(self, items: Sequence[MenuBarItem]) -> None:
        """Refresh the open popup when a visible item's property changes."""

        def on_change(_value) -> None:
            self._refresh_open_menu()

        def walk(entries: Sequence[MenuBarItem]) -> None:
            for entry in entries:
                for prop in (entry.label, entry.enabled, entry.checked):
                    if isinstance(prop, ObservableBase):
                        self._open_subscriptions.append(prop.subscribe(on_change))
                if entry.submenu is not None:
                    walk(entry.submenu)

        walk(items)

    def _dispose_open_subscriptions(self) -> None:
        subscriptions, self._open_subscriptions = self._open_subscriptions, []
        for subscription in subscriptions:
            dispose = getattr(subscription, "dispose", None)
            if callable(dispose):
                dispose()

    def _refresh_open_menu(self) -> None:
        if self._open_index is not None:
            self.open_menu(self._open_index)

    # ---- Popup adapter ----------------------------------------------------------

    def _build_popup_entries(self, items: Sequence[MenuBarItem]) -> list:
        """Translate model items into Material Menu widgets.

        The Material widgets' public API is unchanged; only their colors are
        supplied from the menu bar palette via the derived ``MenuStyle``.
        """
        entries: list = []
        for item in items:
            if item.is_separator:
                entries.append(MenuDivider())
            elif item.submenu is not None:
                entries.append(
                    SubMenuItem(
                        item.resolved_label(),
                        items=self._build_popup_entries(item.submenu),
                        disabled=not item.resolved_enabled(),
                    )
                )
            else:
                checked = item.checked is not None and bool(item.checked.value)
                entries.append(
                    MenuItem(
                        item.resolved_label(),
                        on_click=self._make_popup_activate(item),
                        disabled=not item.resolved_enabled(),
                        leading_icon=Symbols.check if checked else None,
                        trailing=item.shortcut.display if item.shortcut is not None else None,
                    )
                )
        return entries

    def _make_popup_activate(self, item: MenuBarItem):
        def on_click() -> None:
            self.activate(item)

        return on_click

    def popup_style(self) -> MenuStyle:
        """Derive the popup ``MenuStyle`` from the menu bar palette."""
        palette = self._palette
        return MenuStyle(
            background=palette.popup_background,
            label_color=palette.popup_foreground,
            icon_color=palette.popup_foreground,
            trailing_text_color=palette.popup_accelerator,
            disabled_color=palette.popup_disabled_foreground,
            state_layer_color=palette.popup_state_layer,
            divider_color=palette.popup_divider,
            corner_radius=self._style.popup_corner_radius,
            min_width=self._style.popup_min_width,
        )


class _MenuBarTopItem(InteractiveWidget):
    """One top-level bar entry: a clickable title that opens its popup."""

    def __init__(
        self,
        bar: MenuBarWidget,
        index: int,
        item: MenuBarItem,
        palette: MenuBarThemeData,
        style: MenuBarStyle,
    ) -> None:
        self._bar = bar
        self._index = index
        self._item = item
        self._open_background = palette.bar_open_background
        label = item.label if isinstance(item.label, ObservableBase) else item.resolved_label()
        text = Text(
            label,
            style=TextStyle(color=palette.bar_foreground),
            type_scale=TypeScaleToken.from_size(style.label_size),
        )
        pad = style.item_horizontal_padding
        super().__init__(
            child=Container(
                child=text,
                height=Sizing.weight(),
                padding=(pad, 0, pad, 0),
                alignment="center",
            ),
            on_click=lambda: bar.toggle_menu(index),
            on_hover=self._handle_hover,
            disabled=_inverted(item.enabled),
            state_layer_color=palette.bar_state_layer,
            height=Sizing.weight(),
            corner_radius=style.item_corner_radius,
        )

    def _handle_hover(self, hovered: bool) -> None:
        if hovered:
            self._bar.top_item_hovered(self._index)

    def set_open(self, is_open: bool) -> None:
        """Highlight the title while its menu is open."""
        self.bgcolor = self._open_background if is_open else None
        self.invalidate()

    def on_key_event(self, key: str, modifier_keys: int = 0) -> bool:
        if self.disabled:
            return False
        if key == "down":
            self._bar.open_menu(self._index, via_keyboard=True)
            return True
        if key in ("enter", "space"):
            self._bar.toggle_menu(self._index, via_keyboard=True)
            return True
        return super().on_key_event(key, modifier_keys)


class _MenuBarPopup(Menu):
    """The top-level popup: a Material Menu that also walks the bar.

    Unconsumed Left/Right at the top popup level switch to the adjacent
    top-level menu — ``Menu`` itself only consumes them for entering and
    leaving a submenu.
    """

    def __init__(self, bar: MenuBarWidget, entries: list) -> None:
        self._bar = bar
        self._remount_focus_index = -1
        super().__init__(entries, on_dismiss=bar.close_menu, style=bar.popup_style())

    def on_key_event(self, key: str, modifier_keys: int = 0) -> bool:
        if super().on_key_event(key, modifier_keys):
            return True
        key_name = str(key).lower()
        if key_name == "left":
            return self._bar.switch(-1)
        if key_name == "right":
            return self._bar.switch(1)
        return False

    def on_unmount(self) -> None:
        # The overlay rebuilds its layer stack whenever an entry opens or
        # closes (a submenu appearing, a neighbor menu leaving), remounting
        # this popup on the way, and ``Menu.on_unmount`` rightly drops the
        # focus it holds. Remember the focused row so the remount can restore
        # it (see ``_item_mounted``); the bar builds a fresh popup for every
        # open, so a stale index cannot leak into a later open.
        self._remount_focus_index = self._focus_index if self._holds_item_focus() else -1
        super().on_unmount()
        self._bar.popup_gone(self)

    def _item_mounted(self, item) -> None:
        super()._item_mounted(item)
        index = self._remount_focus_index
        if 0 <= index < len(self._focusable_items) and self._focusable_items[index] is item:
            self._remount_focus_index = -1
            self._focus_item(item)
