"""Application menu bar model.

The menu bar is declarative data registered on ``App`` (``App(menu=...)``),
not widgets in the tree: on macOS the global menu bar lives outside the
window, and ``NSMenu`` renders labels, accelerators and check marks — not
widget subtrees. See ``docs/design/MENU_BAR.md``.

Lives in the framework-common ``menubar`` package (not under ``material``):
the menu bar is not a Material Design component, so like the scrollbar it is
a generic widget whose palette arrives through the generic theme seam.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional, Sequence, Tuple, Union

from nuiitivet.input.shortcut import Shortcut, ShortcutLike, to_shortcut
from nuiitivet.observable import MutableObservableBase, ObservableBase
from nuiitivet.widgeting.callbacks import VoidCallback

from .style import MenuBarStyle

#: A property that is either a plain value or an observable one.
ObservableStr = Union[str, ObservableBase[str]]
ObservableBool = Union[bool, ObservableBase[bool]]


def read_value(value):
    """Return ``value.value`` for an observable property, ``value`` otherwise."""
    if isinstance(value, ObservableBase):
        return value.value
    return value


class MenuBarRole(Enum):
    """Built-in command a standard :class:`MenuBarItem` invokes.

    A role item needs no ``on_select``: activating it dispatches the mapped
    built-in intent (see ``nuiitivet.menubar.controller``). Roles are also what
    the macOS bridge will use to relocate items to their conventional places
    (e.g. Quit into the application menu).
    """

    NONE = "none"
    QUIT = "quit"
    CLOSE_WINDOW = "close_window"
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    FULL_SCREEN = "full_screen"


class MenuBarItem:
    """One entry in the application menu bar.

    A single type covers all roles:

    - **Action**: ``MenuBarItem("Open...", on_select=..., shortcut="Accel+O")``
    - **Submenu**: ``MenuBarItem("File", submenu=[...])`` — top-level bar
      entries are simply items with a ``submenu``; nesting is unlimited.
    - **Separator**: ``MenuBarItem.separator()``
    - **Standard item**: ``MenuBarItem.quit()`` and friends — prebuilt items
      whose activation dispatches a built-in intent.

    ``label`` and ``enabled`` may be Observables and propagate live to
    whichever surface renders the model. ``checked`` (presence makes the item
    checkable) must be a *writable* Observable: activation toggles it before
    ``on_select`` runs.

    Args:
        label: Item label; a plain string or an Observable.
        on_select: Called with no arguments when the item is activated. May be
            sync or async. Exactly one of ``on_select`` / ``submenu`` / a
            standard-item role is required for a non-separator item.
        shortcut: Accelerator gesture, as a spec string (``"Accel+S"``) or a
            :class:`~nuiitivet.input.shortcut.Shortcut`. The menu system both
            displays it and registers it; do not register the same gesture
            separately via ``key_shortcut()``.
        enabled: Whether the item can be activated; a bool or an Observable.
        checked: Writable Observable holding the check state. Presence makes
            the item checkable; activation toggles the value, then calls
            ``on_select``.
        submenu: Child entries. Mutually exclusive with ``on_select`` /
            ``shortcut`` / ``checked``.

    Raises:
        ValueError: If the combination of arguments is invalid.
    """

    label: ObservableStr
    on_select: Optional[VoidCallback]
    shortcut: Optional[Shortcut]
    enabled: ObservableBool
    checked: Optional[MutableObservableBase[bool]]
    submenu: Optional[Tuple["MenuBarItem", ...]]
    role: MenuBarRole
    is_separator: bool

    def __init__(
        self,
        label: ObservableStr = "",
        *,
        on_select: Optional[VoidCallback] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
        checked: Optional[MutableObservableBase[bool]] = None,
        submenu: Optional[Sequence["MenuBarItem"]] = None,
        _role: MenuBarRole = MenuBarRole.NONE,
        _separator: bool = False,
    ) -> None:
        self.label = label
        self.on_select = on_select
        self.shortcut = to_shortcut(shortcut) if shortcut is not None else None
        self.enabled = enabled
        self.checked = checked
        self.submenu = tuple(submenu) if submenu is not None else None
        self.role = _role
        self.is_separator = bool(_separator)
        self._validate()

    def _validate(self) -> None:
        if self.is_separator:
            if (
                self.on_select is not None
                or self.shortcut is not None
                or self.checked is not None
                or self.submenu is not None
                or self.role is not MenuBarRole.NONE
            ):
                raise ValueError("A separator MenuBarItem carries no other properties.")
            return

        if self.submenu is not None:
            if self.on_select is not None or self.shortcut is not None or self.checked is not None:
                raise ValueError(
                    "A submenu MenuBarItem cannot also have on_select, shortcut, or checked."
                )
            if self.role is not MenuBarRole.NONE:
                raise ValueError("A submenu MenuBarItem cannot be a standard item.")
            for child in self.submenu:
                if not isinstance(child, MenuBarItem):
                    raise TypeError("submenu entries must be MenuBarItem instances.")
            return

        has_action = self.on_select is not None or self.role is not MenuBarRole.NONE
        if not has_action:
            raise ValueError(
                "A MenuBarItem needs exactly one of on_select, submenu, or a standard-item role."
            )
        if self.on_select is not None and self.role is not MenuBarRole.NONE:
            raise ValueError("A standard MenuBarItem does not take on_select.")

    # ---- Resolved reads ------------------------------------------------

    def resolved_label(self) -> str:
        """The current label text (reads the Observable if there is one)."""
        return str(read_value(self.label))

    def resolved_enabled(self) -> bool:
        """The current enabled state (reads the Observable if there is one)."""
        return bool(read_value(self.enabled))

    # ---- Separator ------------------------------------------------------

    @classmethod
    def separator(cls) -> "MenuBarItem":
        """A horizontal separator line between items."""
        return cls(_separator=True)

    # ---- Standard items --------------------------------------------------
    # Prebuilt commands the framework owns as built-in intents. They absorb
    # platform conventions (labels, accelerators, and — on macOS, once the
    # NSMenu bridge exists — placement), so app code stays platform-free.

    @classmethod
    def quit(
        cls,
        *,
        label: Optional[ObservableStr] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuBarItem":
        """Exit the application (dispatches ``ExitAppIntent``)."""
        if label is None:
            label = "Quit" if sys.platform == "darwin" else "Exit"
        if shortcut is None and sys.platform == "darwin":
            shortcut = "Accel+Q"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuBarRole.QUIT)

    @classmethod
    def close_window(
        cls,
        *,
        label: ObservableStr = "Close Window",
        shortcut: Optional[ShortcutLike] = "Accel+W",
        enabled: ObservableBool = True,
    ) -> "MenuBarItem":
        """Close the window (dispatches ``CloseWindowIntent``)."""
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuBarRole.CLOSE_WINDOW)

    @classmethod
    def minimize(
        cls,
        *,
        label: ObservableStr = "Minimize",
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuBarItem":
        """Minimize the window (dispatches ``MinimizeWindowIntent``)."""
        if shortcut is None and sys.platform == "darwin":
            shortcut = "Accel+M"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuBarRole.MINIMIZE)

    @classmethod
    def maximize(
        cls,
        *,
        label: Optional[ObservableStr] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuBarItem":
        """Maximize / zoom the window (dispatches ``MaximizeWindowIntent``)."""
        if label is None:
            label = "Zoom" if sys.platform == "darwin" else "Maximize"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuBarRole.MAXIMIZE)

    @classmethod
    def full_screen(
        cls,
        *,
        label: ObservableStr = "Full Screen",
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuBarItem":
        """Toggle full screen (dispatches ``FullScreenIntent``)."""
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuBarRole.FULL_SCREEN)


class MenuBar:
    """The application menu bar model: the root of the declarative menu tree.

    Registered on the App (``App(menu=nv.MenuBar([...]))``) and replaced
    wholesale via ``app.menu = ...``. Structure is not observable — item
    *properties* (label / enabled / checked) may be Observables, but adding
    or removing items means assigning a new model.

    Args:
        items: Top-level entries. Bar entries are usually submenus
            (``MenuBarItem("File", submenu=[...])``); a plain action item is
            allowed and activates directly on click.
        style: Optional per-instance style; ``None`` follows the theme.
    """

    def __init__(
        self,
        items: Sequence[MenuBarItem],
        *,
        style: Optional[MenuBarStyle] = None,
    ) -> None:
        entries = tuple(items)
        for entry in entries:
            if not isinstance(entry, MenuBarItem):
                raise TypeError("MenuBar items must be MenuBarItem instances.")
        self.items: Tuple[MenuBarItem, ...] = entries
        self.style = style
