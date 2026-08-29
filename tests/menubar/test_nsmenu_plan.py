"""Tests for the pure half of the macOS NSMenu bridge.

``key_equivalent`` and ``plan_menus`` are platform-free translations, so they
run (and are verified) on every platform — only the Cocoa layer itself is
macOS-only.
"""

from __future__ import annotations

import sys
from typing import Any, List, cast

import pytest

from nuiitivet.input.shortcut import Shortcut
from nuiitivet.layout.column import Column
from nuiitivet.material.text import Text
from nuiitivet.menubar.controller import MenuBarController
from nuiitivet.menubar.model import MenuBar
from nuiitivet.menus import MenuEntry, MenuRole
from nuiitivet.menubar.nsmenu import (
    _NS_COMMAND,
    _NS_CONTROL,
    _NS_SHIFT,
    key_equivalent,
    plan_menus,
)


@pytest.fixture
def darwin(monkeypatch: pytest.MonkeyPatch):
    # ``Accel`` resolves per platform at call time; the bridge only ever runs
    # on macOS, so its translation is pinned there.
    monkeypatch.setattr(sys, "platform", "darwin")


def test_key_equivalent_letters_and_masks(darwin) -> None:
    assert key_equivalent(Shortcut.parse("Accel+S")) == ("s", _NS_COMMAND)
    assert key_equivalent(Shortcut.parse("Accel+Shift+Z")) == ("z", _NS_COMMAND | _NS_SHIFT)
    assert key_equivalent(Shortcut.parse("Ctrl+A")) == ("a", _NS_CONTROL)


def test_key_equivalent_function_and_special_keys(darwin) -> None:
    assert key_equivalent(Shortcut.parse("Accel+F5")) == (chr(0xF708), _NS_COMMAND)
    assert key_equivalent(Shortcut.parse("Accel+PgUp")) == (chr(0xF72C), _NS_COMMAND)
    assert key_equivalent(Shortcut.parse("Accel+Enter")) == ("\r", _NS_COMMAND)


def test_key_equivalent_unmappable_key_is_empty(darwin) -> None:
    assert key_equivalent(Shortcut("f19", 0)) == ("", 0)


def _labels(entries) -> List[str]:
    return [entry.resolved_label() for entry in entries]


def test_plan_relocates_quit_into_app_menu(darwin) -> None:
    quit_item = MenuEntry.quit()
    model = MenuBar(
        [
            MenuEntry(
                "File",
                submenu=[
                    MenuEntry("Open", on_select=lambda: None),
                    MenuEntry.separator(),
                    quit_item,
                ],
            ),
            MenuEntry("Edit", submenu=[MenuEntry("Undo", on_select=lambda: None)]),
        ]
    )
    plans = plan_menus(model, "MyApp")
    assert [plan.title for plan in plans] == ["MyApp", "File", "Edit"]
    assert plans[0].entries == (quit_item,)
    # The separator that led up to Quit does not dangle.
    assert _labels(plans[1].entries) == ["Open"]


def test_plan_synthesizes_quit_when_model_has_none(darwin) -> None:
    model = MenuBar([MenuEntry("File", submenu=[MenuEntry("Open", on_select=lambda: None)])])
    plans = plan_menus(model, "MyApp")
    assert plans[0].title == "MyApp"
    assert len(plans[0].entries) == 1
    assert plans[0].entries[0].role is MenuRole.QUIT


def test_plan_wraps_top_level_action_item(darwin) -> None:
    direct = MenuEntry("About", on_select=lambda: None)
    plans = plan_menus(MenuBar([direct]), "MyApp")
    assert plans[1].title == "About"
    assert plans[1].entries == (direct,)


class _StubBridge:
    def __init__(self) -> None:
        self.installed: List[object] = []

    def install(self, model) -> None:
        self.installed.append(model)


def test_native_bridge_collapses_in_app_slots(nuiitivet_app) -> None:
    model = MenuBar([MenuEntry("File", submenu=[MenuEntry("Open", on_select=lambda: None)])])
    app = nuiitivet_app(Column(children=[Text("content")]), size=(800, 600), menu=model)
    assert app.get(label="File") is not None

    controller: MenuBarController = app.window._menubar_controller
    stub = _StubBridge()
    controller._bridge = cast(Any, stub)
    controller._notify()
    app.settle()
    assert app.query(label="File") is None

    # Replacement reaches the bridge instead of any slot.
    new_model = MenuBar([MenuEntry("View", submenu=[MenuEntry("Zoom", on_select=lambda: None)])])
    app.window.menu = new_model
    app.settle()
    assert stub.installed == [new_model]
    assert app.query(label="View") is None
