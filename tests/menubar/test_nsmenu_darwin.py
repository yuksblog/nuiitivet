"""macOS-only integration tests for the NSMenu bridge's Cocoa layer.

Skipped everywhere but darwin (CI is Linux); they run in the local suite.
The AppKit action path regressed silently once — the action target's ctypes
trampolines were collected, and the resulting failure inside the callback is
swallowed by ctypes ("Exception ignored"), so a click just does nothing —
hence a test that drives the real ``sendAction:to:from:`` dispatch.
"""

from __future__ import annotations

import sys
from typing import List

import pytest

from nuiitivet.material.text import Text
from nuiitivet.menubar.model import MenuBar
from nuiitivet.menus import MenuEntry
from nuiitivet.observable import Observable

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="NSMenu bridge is macOS-only")


def test_appkit_send_action_reaches_on_select(nuiitivet_app) -> None:
    record: List[str] = []
    checked = Observable(False)
    model = MenuBar(
        [
            MenuEntry(
                "File",
                submenu=[
                    MenuEntry("Open", on_select=lambda: record.append("open"), shortcut="Accel+O"),
                    MenuEntry("Wrap", on_select=lambda: record.append("wrap"), checked=checked),
                ],
            )
        ]
    )
    app = nuiitivet_app(Text("content"), size=(400, 300), menu=model)
    controller = app.window._menubar_controller
    controller.install_platform_bridge()
    assert controller.native

    from pyglet.libs.darwin.cocoapy import ObjCClass, get_selector

    bridge = app.app._menubar_focus_coordinator._bridge
    assert bridge is not None
    builder = bridge._builder
    assert builder is not None
    ns_items = {}
    for obj in builder._retained:
        if hasattr(obj, "tag") and obj.action() is not None:
            ns_items[int(obj.tag())] = obj
    by_label = {action.resolved_label(): tag for tag, action in enumerate(builder._actions)}

    ns_app = ObjCClass("NSApplication").sharedApplication()
    selector = get_selector("nuiitivetMenuAction:")

    assert ns_app.sendAction_to_from_(selector, builder._target, ns_items[by_label["Open"]])
    assert record == ["open"]

    assert ns_app.sendAction_to_from_(selector, builder._target, ns_items[by_label["Wrap"]])
    assert record == ["open", "wrap"]
    assert checked.value is True
    # Pump the clock so the scheduled NSMenuItem state sync runs; it must
    # also have marked the item checked.
    app.settle()
    assert int(ns_items[by_label["Wrap"]].state()) == 1


def test_main_menu_structure_matches_plan(nuiitivet_app) -> None:
    model = MenuBar(
        [
            MenuEntry(
                "File",
                submenu=[
                    MenuEntry("Open", on_select=lambda: None),
                    MenuEntry.separator(),
                    MenuEntry.quit(),
                ],
            ),
            MenuEntry("Edit", submenu=[MenuEntry("Undo", on_select=lambda: None)]),
        ]
    )
    app = nuiitivet_app(Text("content"), size=(400, 300), menu=model)
    controller = app.window._menubar_controller
    controller.install_platform_bridge()

    from pyglet.libs.darwin.cocoapy import ObjCClass, cfstring_to_string

    main = ObjCClass("NSApplication").sharedApplication().mainMenu()
    titles = [
        cfstring_to_string(main.itemAtIndex_(i).title()) for i in range(int(main.numberOfItems()))
    ]
    # App menu first (holding the relocated Quit), then the author's menus.
    assert titles[1:] == ["File", "Edit"]
    file_menu = main.itemAtIndex_(1).submenu()
    # Quit left File; the trailing separator went with it.
    assert int(file_menu.numberOfItems()) == 1
