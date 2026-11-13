"""Declarative menu model shared by every menu surface.

:class:`MenuEntry` describes one entry of a menu as plain data — label,
action, shortcut, check state, submenu — without prescribing how it is
rendered. The application menu bar (``nuiitivet.menubar``) and the system
tray icon (``nuiitivet.platform.tray``) both consume this model; the bar
draws framework widgets (or bridges to ``NSMenu`` on macOS via the shared
:mod:`nuiitivet.menus.nsmenu` translation) while the tray menu is native on
every platform.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional, Sequence, Tuple, Union

from nuiitivet.input.shortcut import Shortcut, ShortcutLike, to_shortcut
from nuiitivet.observable import MutableStateBase, StateBase
from nuiitivet.widgeting.callbacks import VoidCallback

#: A property that is either a plain value or a State of it.
StrOrState = Union[str, StateBase[str]]
BoolOrState = Union[bool, StateBase[bool]]


def read_value(value):
    """Return ``value.value`` for a State property, ``value`` otherwise."""
    if isinstance(value, StateBase):
        return value.value
    return value


class MenuRole(Enum):
    """Built-in command a standard :class:`MenuEntry` invokes.

    A role entry needs no ``on_select``: activating it calls the mapped
    built-in method (see ``nuiitivet.menubar.controller``). Roles are also what
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
    - **Standard item**: ``MenuEntry.quit()``, ``close_window()``,
      ``minimize()``, ``maximize()``, ``restore()``, ``full_screen()`` —
      prebuilt entries whose activation calls a built-in App/Window method.

    ``label`` and ``enabled`` may be States and propagate live to
    whichever surface renders the model. ``checked`` (presence makes the entry
    checkable) must be a *writable* State: activation toggles it before
    ``on_select`` runs.
    """

    label: StrOrState
    on_select: Optional[VoidCallback]
    shortcut: Optional[Shortcut]
    enabled: BoolOrState
    checked: Optional[MutableStateBase[bool]]
    submenu: Optional[Tuple["MenuEntry", ...]]
    role: MenuRole
    is_separator: bool

    def __init__(
        self,
        label: StrOrState = "",
        *,
        on_select: Optional[VoidCallback] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: BoolOrState = True,
        checked: Optional[MutableStateBase[bool]] = None,
        submenu: Optional[Sequence["MenuEntry"]] = None,
        _role: MenuRole = MenuRole.NONE,
        _separator: bool = False,
    ) -> None:
        """Initialize MenuEntry.

        Args:
            label: Entry label; a plain string or a State.
            on_select: Called with no arguments when the entry is activated. May be
                sync or async. Exactly one of ``on_select`` / ``submenu`` / a
                standard-item role is required for a non-separator entry.
            shortcut: Accelerator gesture, as a spec string (``"Accel+S"``) or a
                :class:`~nuiitivet.input.shortcut.Shortcut`. The menu system both
                displays it and registers it; do not register the same gesture
                separately via ``key_shortcut()``.
            enabled: Whether the entry can be activated; a bool or a State.
            checked: Writable State holding the check state. Presence makes
                the entry checkable; activation toggles the value, then calls
                ``on_select``.
            submenu: Child entries. Mutually exclusive with ``on_select`` /
                ``shortcut`` / ``checked``.

        Raises:
            ValueError: If the combination of arguments is invalid.
        """
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
        """The current label text (reads the State if there is one)."""
        return str(read_value(self.label))

    def resolved_enabled(self) -> bool:
        """The current enabled state (reads the State if there is one)."""
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
        label: Optional[StrOrState] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: BoolOrState = True,
    ) -> "MenuEntry":
        """Exit the application (calls ``app.exit()``).

        Args:
            label: Entry label. Defaults to "Quit" on macOS, "Exit" elsewhere.
            shortcut: Accelerator gesture. Defaults to ``"Accel+Q"`` on macOS, none elsewhere.
            enabled: Whether the entry can be activated; a bool or a State.
        """
        if label is None:
            label = "Quit" if sys.platform == "darwin" else "Exit"
        if shortcut is None and sys.platform == "darwin":
            shortcut = "Accel+Q"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.QUIT)

    @classmethod
    def close_window(
        cls,
        *,
        label: StrOrState = "Close Window",
        shortcut: Optional[ShortcutLike] = "Accel+W",
        enabled: BoolOrState = True,
    ) -> "MenuEntry":
        """Close the window (calls ``window.close()``).

        Args:
            label: Entry label. Defaults to "Close Window".
            shortcut: Accelerator gesture. Defaults to ``"Accel+W"``; ``None`` for none.
            enabled: Whether the entry can be activated; a bool or a State.
        """
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.CLOSE_WINDOW)

    @classmethod
    def minimize(
        cls,
        *,
        label: StrOrState = "Minimize",
        shortcut: Optional[ShortcutLike] = None,
        enabled: BoolOrState = True,
    ) -> "MenuEntry":
        """Minimize the window (calls ``window.minimize()``).

        Args:
            label: Entry label. Defaults to "Minimize".
            shortcut: Accelerator gesture. Defaults to ``"Accel+M"`` on macOS, none elsewhere.
            enabled: Whether the entry can be activated; a bool or a State.
        """
        if shortcut is None and sys.platform == "darwin":
            shortcut = "Accel+M"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.MINIMIZE)

    @classmethod
    def maximize(
        cls,
        *,
        label: Optional[StrOrState] = None,
        shortcut: Optional[ShortcutLike] = None,
        enabled: BoolOrState = True,
    ) -> "MenuEntry":
        """Maximize / zoom the window (calls ``window.maximize()``).

        Args:
            label: Entry label. Defaults to "Zoom" on macOS, "Maximize" elsewhere.
            shortcut: Accelerator gesture. None by default.
            enabled: Whether the entry can be activated; a bool or a State.
        """
        if label is None:
            label = "Zoom" if sys.platform == "darwin" else "Maximize"
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.MAXIMIZE)

    @classmethod
    def restore(
        cls,
        *,
        label: StrOrState = "Restore",
        shortcut: Optional[ShortcutLike] = None,
        enabled: BoolOrState = True,
    ) -> "MenuEntry":
        """Restore the window (calls ``window.restore()``).

        The way back from :meth:`full_screen`, :meth:`maximize`, and
        :meth:`minimize`: exits full screen, or restores the pre-maximize
        size, or brings a minimized window back.

        Args:
            label: Entry label. Defaults to "Restore".
            shortcut: Accelerator gesture. None by default.
            enabled: Whether the entry can be activated; a bool or a State.
        """
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.RESTORE)

    @classmethod
    def full_screen(
        cls,
        *,
        label: StrOrState = "Full Screen",
        shortcut: Optional[ShortcutLike] = None,
        enabled: BoolOrState = True,
    ) -> "MenuEntry":
        """Toggle full screen (calls ``window.full_screen()``).

        Args:
            label: Entry label. Defaults to "Full Screen".
            shortcut: Accelerator gesture. None by default.
            enabled: Whether the entry can be activated; a bool or a State.
        """
        return cls(label, shortcut=shortcut, enabled=enabled, _role=MenuRole.FULL_SCREEN)
