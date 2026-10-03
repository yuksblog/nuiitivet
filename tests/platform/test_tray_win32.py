"""Tests for the Windows tray backend.

The menu plan and the icon decode make no Win32 call and run on every
platform. The smoke tests at the bottom are Windows-only: CI runs on Linux,
so run them manually on a Windows machine. They put a real icon in the
notification area for a moment and never open the menu.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import skia as _skia

from nuiitivet.menus import MenuEntry
from nuiitivet.observable import Observable
from nuiitivet.platform.tray import TrayIcon
from nuiitivet.platform.tray_win32_plan import (
    MF_CHECKED,
    MF_GRAYED,
    MF_POPUP,
    MF_SEPARATOR,
    MF_STRING,
    load_icon_bgra,
    plan_menu,
)

# The skia stub covers only what src/ uses.
skia: Any = _skia

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Win32 tray backend is Windows-only")


# ---- Menu plan --------------------------------------------------------------


def test_plan_maps_each_action_to_its_own_command_id() -> None:
    open_entry = MenuEntry("Open", on_select=lambda: None)
    child = MenuEntry("Child", on_select=lambda: None)
    quit_entry = MenuEntry.quit()
    items, commands = plan_menu(
        [
            open_entry,
            MenuEntry.separator(),
            MenuEntry("More", submenu=[child]),
            quit_entry,
        ]
    )

    open_item, separator, more, quit_item = items
    assert (open_item.label, open_item.flags) == ("Open", MF_STRING)
    assert (separator.flags, separator.command_id) == (MF_SEPARATOR, 0)
    assert (more.flags, more.command_id) == (MF_STRING | MF_POPUP, 0)
    assert commands == {
        open_item.command_id: open_entry,
        more.children[0].command_id: child,
        quit_item.command_id: quit_entry,
    }
    # 0 is what TrackPopupMenu returns for a dismissed menu.
    assert 0 not in commands
    assert len(commands) == 3


def test_plan_reads_observables_at_plan_time() -> None:
    label = Observable("Ping (0)")
    enabled = Observable(True)
    checked = Observable(False)
    menu = [MenuEntry(label, on_select=lambda: None, enabled=enabled, checked=checked)]

    (before,), _ = plan_menu(menu)
    assert (before.label, before.flags) == ("Ping (0)", MF_STRING)

    label.value = "Ping (1)"
    enabled.value = False
    checked.value = True
    (after,), _ = plan_menu(menu)
    assert (after.label, after.flags) == ("Ping (1)", MF_STRING | MF_GRAYED | MF_CHECKED)


def test_plan_greys_a_disabled_submenu() -> None:
    (more,), _ = plan_menu(
        [MenuEntry("More", enabled=False, submenu=[MenuEntry("Child", on_select=lambda: None)])]
    )
    assert more.flags == MF_STRING | MF_GRAYED | MF_POPUP


def test_plan_escapes_ampersand() -> None:
    (item,), _ = plan_menu([MenuEntry("Save & Quit", on_select=lambda: None)])
    assert item.label == "Save && Quit"


def test_plan_of_empty_menu_is_empty() -> None:
    assert plan_menu([]) == ((), {})


# ---- Icon decode ------------------------------------------------------------


def _write_png(path: Path, size: int, color: int) -> None:
    surface = skia.Surface(size, size)
    surface.getCanvas().clear(color)
    surface.makeImageSnapshot().save(str(path), skia.kPNG)


def test_icon_decodes_to_bgra_with_straight_alpha(tmp_path: Path) -> None:
    path = tmp_path / "icon.png"
    _write_png(path, 16, skia.Color(255, 0, 0, 128))

    pixels = load_icon_bgra(path, 16)
    assert pixels is not None
    assert len(pixels) == 16 * 16 * 4
    blue, green, red, alpha = pixels[:4]
    assert (blue, green, alpha) == (0, 0, 128)
    assert red >= 254  # not premultiplied down to 128


def test_icon_is_scaled_to_the_requested_size(tmp_path: Path) -> None:
    path = tmp_path / "icon.png"
    _write_png(path, 64, skia.Color(0, 0, 255, 255))

    pixels = load_icon_bgra(path, 16)
    assert pixels is not None
    assert len(pixels) == 16 * 16 * 4
    assert tuple(pixels[:4]) == (255, 0, 0, 255)


def test_icon_that_cannot_be_decoded_is_none(tmp_path: Path) -> None:
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not an image")
    assert load_icon_bgra(broken, 16) is None
    assert load_icon_bgra(tmp_path / "missing.png", 16) is None


# ---- Windows smoke tests ----------------------------------------------------


@windows_only
def test_selected_bridge_is_win32() -> None:
    from nuiitivet.platform.tray_win32 import TrayWin32Bridge

    assert isinstance(TrayIcon()._create_bridge(), TrayWin32Bridge)


@windows_only
def test_bridge_installs_and_uninstalls() -> None:
    from nuiitivet.platform.tray_win32 import TrayWin32Bridge, active_bridge

    tooltip = Observable("nuiitivet test")
    bridge = TrayWin32Bridge(TrayIcon(tooltip=tooltip, menu=[MenuEntry.quit()]))
    bridge.install()
    try:
        assert active_bridge() is bridge
        tooltip.value = "nuiitivet test (changed)"
        assert bridge.show_balloon("Title", "Body") is True
    finally:
        bridge.uninstall()
    assert active_bridge() is None
    assert bridge.show_balloon("Title", "Body") is False


@windows_only
def test_bridge_installs_again_after_uninstall() -> None:
    from nuiitivet.platform.tray_win32 import TrayWin32Bridge

    for _ in range(2):
        bridge = TrayWin32Bridge(TrayIcon())
        bridge.install()
        bridge.uninstall()


@windows_only
def test_bridge_builds_icon_from_png(tmp_path: Path) -> None:
    from nuiitivet.platform.tray_win32 import TrayWin32Bridge

    path = tmp_path / "icon.png"
    _write_png(path, 64, skia.Color(0, 128, 255, 255))
    bridge = TrayWin32Bridge(TrayIcon(icon=path))
    bridge.install()
    try:
        assert vars(bridge)["_owns_icon"] is True
    finally:
        bridge.uninstall()
