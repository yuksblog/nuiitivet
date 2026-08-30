"""Declarative menu model shared by every menu surface.

:class:`MenuEntry` describes one entry of a menu as plain data, consumed by
the application menu bar (``nuiitivet.menubar``) and the system tray icon
(``nuiitivet.platform.tray``). The shared ``MenuEntry`` → ``NSMenu``
translation both native surfaces use lives in :mod:`nuiitivet.menus.nsmenu`.
"""

from __future__ import annotations

from .model import MenuEntry, MenuRole, ObservableBool, ObservableStr, read_value

__all__ = ["MenuEntry", "MenuRole", "ObservableBool", "ObservableStr", "read_value"]
