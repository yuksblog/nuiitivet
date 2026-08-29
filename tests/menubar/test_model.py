"""Tests for the menu bar model: validation, factories, resolved reads."""

from __future__ import annotations

import sys

import pytest

from nuiitivet.input.shortcut import Shortcut
from nuiitivet.menubar.model import MenuBar
from nuiitivet.menus import MenuEntry, MenuRole
from nuiitivet.menubar.style import MenuBarStyle
from nuiitivet.observable import Observable


def test_action_item_normalizes_shortcut() -> None:
    item = MenuEntry("Open...", on_select=lambda: None, shortcut="Accel+O")
    assert isinstance(item.shortcut, Shortcut)
    assert item.shortcut.key == "o"


def test_item_requires_an_action() -> None:
    with pytest.raises(ValueError):
        MenuEntry("Nothing")


def test_submenu_excludes_action_properties() -> None:
    child = MenuEntry("Child", on_select=lambda: None)
    with pytest.raises(ValueError):
        MenuEntry("File", submenu=[child], on_select=lambda: None)
    with pytest.raises(ValueError):
        MenuEntry("File", submenu=[child], shortcut="Accel+F")
    with pytest.raises(ValueError):
        MenuEntry("File", submenu=[child], checked=Observable(False))


def test_separator_carries_nothing_else() -> None:
    separator = MenuEntry.separator()
    assert separator.is_separator
    with pytest.raises(ValueError):
        MenuEntry(on_select=lambda: None, _separator=True)


def test_standard_item_rejects_on_select() -> None:
    with pytest.raises(ValueError):
        MenuEntry("Quit", on_select=lambda: None, _role=MenuRole.QUIT)


def test_submenu_entries_must_be_items() -> None:
    with pytest.raises(TypeError):
        MenuEntry("File", submenu=["not an item"])  # type: ignore[list-item]


def test_quit_factory_is_platform_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    quit_mac = MenuEntry.quit()
    assert quit_mac.role is MenuRole.QUIT
    assert quit_mac.resolved_label() == "Quit"
    assert quit_mac.shortcut is not None and quit_mac.shortcut.key == "q"

    monkeypatch.setattr(sys, "platform", "win32")
    quit_win = MenuEntry.quit()
    assert quit_win.resolved_label() == "Exit"
    assert quit_win.shortcut is None


def test_standard_factories_set_roles() -> None:
    assert MenuEntry.close_window().role is MenuRole.CLOSE_WINDOW
    assert MenuEntry.minimize().role is MenuRole.MINIMIZE
    assert MenuEntry.maximize().role is MenuRole.MAXIMIZE
    assert MenuEntry.restore().role is MenuRole.RESTORE
    assert MenuEntry.full_screen().role is MenuRole.FULL_SCREEN


def test_resolved_reads_follow_observables() -> None:
    label = Observable("Save")
    enabled = Observable(False)
    item = MenuEntry(label, on_select=lambda: None, enabled=enabled)
    assert item.resolved_label() == "Save"
    assert item.resolved_enabled() is False
    label.value = "Save All"
    enabled.value = True
    assert item.resolved_label() == "Save All"
    assert item.resolved_enabled() is True


def test_menu_bar_validates_items_and_keeps_style() -> None:
    style = MenuBarStyle(bar_height=40)
    bar = MenuBar([MenuEntry("File", submenu=[MenuEntry.quit()])], style=style)
    assert bar.style is style
    with pytest.raises(TypeError):
        MenuBar(["File"])  # type: ignore[list-item]
