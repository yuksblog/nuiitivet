"""Tests for the pystray tray bridge, against a stub pystray module.

pystray is installed only on Windows/Linux, and the real thing needs a
desktop tray host to do anything, so the backend contract is tested against
a stub on every platform: menu translation, the ``update_menu`` refresh on
Observable changes, the ``HAS_MENU`` install refusal, and the
``HAS_DEFAULT`` on_activate degradation.
"""

from __future__ import annotations

import sys
import types
from typing import Any, List

import pytest

from nuiitivet.menus import MenuEntry
from nuiitivet.observable import Observable
from nuiitivet.platform.tray import TrayIcon
from nuiitivet.platform.tray_pystray import TrayPystrayBridge


def _fake_pystray(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Install stub ``pystray`` and ``PIL`` modules; return the pystray stub."""

    class Menu:
        SEPARATOR = object()

        def __init__(self, *items: Any) -> None:
            self.items = items

    class MenuItem:
        def __init__(
            self,
            text: Any,
            action: Any,
            checked: Any = None,
            enabled: Any = None,
            default: bool = False,
            visible: bool = True,
        ) -> None:
            self.text = text
            self.action = action
            self.checked = checked
            self.enabled = enabled
            self.default = default
            self.visible = visible

    class Icon:
        HAS_MENU = True
        HAS_DEFAULT = True
        instances: List["Icon"] = []

        def __init__(self, name: str, image: Any, title: str = "", menu: Any = None) -> None:
            self.name = name
            self.image = image
            self.title = title
            self.menu = menu
            self.update_menu_calls = 0
            self.detached = False
            self.stopped = False
            Icon.instances.append(self)

        def run_detached(self) -> None:
            self.detached = True

        def update_menu(self) -> None:
            self.update_menu_calls += 1

        def stop(self) -> None:
            self.stopped = True

    pystray = types.ModuleType("pystray")
    pystray.Icon = Icon  # type: ignore[attr-defined]
    pystray.Menu = Menu  # type: ignore[attr-defined]
    pystray.MenuItem = MenuItem  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pystray", pystray)

    pil = types.ModuleType("PIL")
    pil.Image = types.SimpleNamespace(  # type: ignore[attr-defined]
        new=lambda *args, **kwargs: "placeholder-image",
        open=lambda path: "file-image",
    )
    monkeypatch.setitem(sys.modules, "PIL", pil)
    return pystray


def test_menu_translation_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    pystray = _fake_pystray(monkeypatch)
    checked = Observable(True)
    tray = TrayIcon(
        menu=[
            MenuEntry("Open", on_select=lambda: None),
            MenuEntry.separator(),
            MenuEntry("Muted", on_select=lambda: None, checked=checked),
            MenuEntry("More", submenu=[MenuEntry("Child", on_select=lambda: None)]),
        ]
    )
    bridge = TrayPystrayBridge(tray)
    bridge.install()

    icon = pystray.Icon.instances[-1]
    assert icon.detached
    open_item, separator, muted, more = icon.menu.items
    assert open_item.text(None) == "Open"
    assert separator is pystray.Menu.SEPARATOR
    assert muted.checked(None) is True
    assert isinstance(more.action, pystray.Menu)
    assert more.action.items[0].text(None) == "Child"


def test_observable_change_triggers_update_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    pystray = _fake_pystray(monkeypatch)
    label = Observable("Ping (0)")
    tray = TrayIcon(menu=[MenuEntry(label, on_select=lambda: None)])
    bridge = TrayPystrayBridge(tray)
    bridge.install()

    icon = pystray.Icon.instances[-1]
    assert icon.update_menu_calls == 0
    label.value = "Ping (1)"
    assert icon.update_menu_calls == 1

    bridge.uninstall()
    label.value = "Ping (2)"  # subscriptions dropped with the bridge
    assert icon.update_menu_calls == 1
    assert icon.stopped


def test_menu_without_backend_menu_support_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    pystray = _fake_pystray(monkeypatch)
    monkeypatch.setattr(pystray.Icon, "HAS_MENU", False)
    tray = TrayIcon(menu=[MenuEntry.quit()])
    with pytest.raises(RuntimeError):
        TrayPystrayBridge(tray).install()
    # Through the model the failure is a logged no-op with installed False.
    monkeypatch.setattr(TrayIcon, "_create_bridge", lambda self: TrayPystrayBridge(self))

    class _App:  # weakref-able stand-in; only used for QUIT dispatch
        pass

    tray2 = TrayIcon(menu=[MenuEntry.quit()])
    tray2._install(_App())  # type: ignore[arg-type]
    assert tray2.installed.value is False


def test_on_activate_without_default_action_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pystray = _fake_pystray(monkeypatch)
    monkeypatch.setattr(pystray.Icon, "HAS_DEFAULT", False)
    tray = TrayIcon(menu=[MenuEntry.quit()], on_activate=lambda: None)
    TrayPystrayBridge(tray).install()

    icon = pystray.Icon.instances[-1]
    assert all(not item.default for item in icon.menu.items)


def test_on_activate_becomes_invisible_default_item(monkeypatch: pytest.MonkeyPatch) -> None:
    pystray = _fake_pystray(monkeypatch)
    tray = TrayIcon(menu=[MenuEntry.quit()], on_activate=lambda: None)
    TrayPystrayBridge(tray).install()

    icon = pystray.Icon.instances[-1]
    default = icon.menu.items[0]
    assert default.default and not default.visible
