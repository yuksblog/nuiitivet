"""Declarative menu model shared by every menu surface.

:class:`MenuEntry` describes one entry of a menu as plain data — label,
action, shortcut, check state, submenu — without prescribing how it is
rendered. The application menu bar (``nuiitivet.menubar``) and the system
tray icon (``nuiitivet.platform.tray``) both consume this model; the bar
draws framework widgets (or bridges to ``NSMenu`` on macOS) while the tray
menu is native on every platform. See ``docs/design/MENU_BAR.md`` and
``docs/design/TRAY_ICON.md``.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional, Sequence, Tuple, Union

from nuiitivet.input.shortcut import Shortcut, ShortcutLike, to_shortcut
from nuiitivet.observable import MutableObservableBase, ObservableBase
from nuiitivet.widgeting.callbacks import VoidCallback

#: A property that is either a plain value or an observable one.
ObservableStr = Union[str, ObservableBase[str]]
ObservableBool = Union[bool, ObservableBase[bool]]


def read_value(value):
    """Return ``value.value`` for an observable property, ``value`` otherwise."""
    if isinstance(value, ObservableBase):
        return value.value
    return value


class MenuRole(Enum):
    """Built-in command a standard :class:`MenuEntry` invokes.

    A role entry needs no ``on_select``: activating it dispatches the mapped
    built-in intent (see ``nuiitivet.menubar.controller``). Roles are also what
    the macOS bridge will use to relocate items to their conventional places
    (e.g. Quit into the application menu).
    """

    NONE = "none"
    QUIT = "quit"
    CLOSE_WINDOW = "close_window"
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    RESTORE = "restore"
    FULL_SCREEN = "full_screen"


class MenuEntry:
    """One entry in a declarative menu model.

    A single type covers all roles:

    - **Action**: ``MenuEntry("Open...", on_select=..., shortcut="Accel+O")``
    - **Submenu**: ``MenuEntry("File", submenu=[...])`` — top-level bar
      entries are simply entries with a ``submenu``; nesting is unlimited.
    - **Separator**: ``MenuEntry.separator()``
    - **Standard item**: ``MenuEntry.quit()`` and friends — prebuilt entries
      whose activation dispatches a built-in intent.

    ``label`` and ``enabled`` may be Observables and propagate live to
    whichever surface renders the model. ``checked`` (presence makes the entry
    checkable) must be a *writable* Observable: activation toggles it before
    ``on_select`` runs.

    Args:
        label: Entry label; a plain string or an Observable.
        on_select: Called with no arguments when the entry is activated. May be
            sync or async. Exactly one of ``on_select`` / ``submenu`` / a
            standard-item role is required for a non-separator entry.
        shortcut: Accelerator gesture, as a spec string (``"Accel+S"``) or a
            :class:`~nuiitivet.input.shortcut.Shortcut`. The menu system both
            displays it and registers it; do not register the same gesture
            separately via ``key_shortcut()``.
        enabled: Whether the entry can be activated; a bool or an Observable.
        checked: Writable Observable holding the check state. Presence makes
            the entry checkable; activation toggles the value, then calls
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
    submenu: Optional[Tuple["MenuEntry", ...]]
    role: MenuRole
    is_separator: bool

    def __init__(
        self,
        label: ObservableStr = "",
        *,
        on_select: Optional[VoidCallback] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
        checked: Optional[MutableObservableBase[bool]] = None,
        submenu: Optional[Sequence["MenuEntry"]] = None,
        _role: MenuRole = MenuRole.NONE,
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
                or self.role is not MenuRole.NONE
            ):
                raise ValueError("A separator MenuEntry carries no other properties.")
            return

        if self.submenu is not None:
            if self.on_select is not None or self.shortcut is not None or self.checked is not None:
                raise ValueError(
                    "A submenu MenuEntry cannot also have on_select, shortcut, or checked."
                )
            if self.role is not MenuRole.NONE:
                raise ValueError("A submenu MenuEntry cannot be a standard item.")
            for child in self.submenu:
                if not isinstance(child, MenuEntry):
                    raise TypeError("submenu entries must be MenuEntry instances.")
            return

        has_action = self.on_select is not None or self.role is not MenuRole.NONE
        if not has_action:
            raise ValueError(
                "A MenuEntry needs exactly one of on_select, submenu, or a standard-item role."
            )
        if self.on_select is not None and self.role is not MenuRole.NONE:
            raise ValueError("A standard MenuEntry does not take on_select.")

    # ---- Resolved reads ------------------------------------------------

    def resolved_label(self) -> str:
        """The current label text (reads the Observable if there is one)."""
        return str(read_value(self.label))

    def resolved_enabled(self) -> bool:
        """The current enabled state (reads the Observable if there is one)."""
        return bool(read_value(self.enabled))

    # ---- Separator ------------------------------------------------------

    @classmethod
    def separator(cls) -> "MenuEntry":
        """A horizontal separator line between entries."""
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
    ) -> "MenuEntry":
        """Exit the application (dispatches ``ExitAppIntent``)."""
        if label is None:
            label = "Quit" if sys.platform == "darwin" else "Exit"
        if shortcut is None and sys.platform == "darwin":
            shortcut = "Accel+Q"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.QUIT)

    @classmethod
    def close_window(
        cls,
        *,
        label: ObservableStr = "Close Window",
        shortcut: Optional[ShortcutLike] = "Accel+W",
        enabled: ObservableBool = True,
    ) -> "MenuEntry":
        """Close the window (dispatches ``CloseWindowIntent``)."""
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.CLOSE_WINDOW)

    @classmethod
    def minimize(
        cls,
        *,
        label: ObservableStr = "Minimize",
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuEntry":
        """Minimize the window (dispatches ``MinimizeWindowIntent``)."""
        if shortcut is None and sys.platform == "darwin":
            shortcut = "Accel+M"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.MINIMIZE)

    @classmethod
    def maximize(
        cls,
        *,
        label: Optional[ObservableStr] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuEntry":
        """Maximize / zoom the window (dispatches ``MaximizeWindowIntent``)."""
        if label is None:
            label = "Zoom" if sys.platform == "darwin" else "Maximize"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.MAXIMIZE)

    @classmethod
    def restore(
        cls,
        *,
        label: ObservableStr = "Restore",
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuEntry":
        """Restore the window (dispatches ``RestoreWindowIntent``).

        The way back from :meth:`full_screen`, :meth:`maximize`, and
        :meth:`minimize`: exits full screen, or restores the pre-maximize
        size, or brings a minimized window back.
        """
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.RESTORE)

    @classmethod
    def full_screen(
        cls,
        *,
        label: ObservableStr = "Full Screen",
        shortcut: Optional[ShortcutLike] = None,
        enabled: ObservableBool = True,
    ) -> "MenuEntry":
        """Toggle full screen (dispatches ``FullScreenIntent``)."""
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.FULL_SCREEN)
