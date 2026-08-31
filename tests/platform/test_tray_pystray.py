"""Tests for the pystray tray bridge, against a stub pystray module.

pystray is installed only on Windows/Linux, and the real thing needs a
desktop tray host to do anything, so the backend contract is tested against
a stub on every platform: menu translation, the ``update_menu`` refresh on
Observable changes, the ``HAS_MENU`` install refusal, the ``HAS_DEFAULT``
on_activate degradation, and the GLib pump the GTK-family backends need.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Callable, List

import pytest

from nuiitivet.menus import MenuEntry
from nuiitivet.observable import Observable, runtime
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


# ---- GLib pump (Linux GTK-family backends) ---------------------------------


class _RecordingClock:
    """Records scheduled/unscheduled callbacks in place of the runtime clock."""

    def __init__(self) -> None:
        self.scheduled: List[Callable[[float], None]] = []
        self.unscheduled: List[Callable[[float], None]] = []

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        self.scheduled.append(fn)

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        self.scheduled.append(fn)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self.unscheduled.append(fn)


class _FakeMainContext:
    """GLib main context whose queued sources are drained by ``iteration``."""

    def __init__(self, queued: int) -> None:
        self.queued = queued
        self.iterations = 0

    def pending(self) -> bool:
        return self.queued > 0

    def iteration(self, may_block: bool) -> None:
        assert may_block is False, "the pump must never block the UI thread"
        self.queued -= 1
        self.iterations += 1


def _fake_glib(monkeypatch: pytest.MonkeyPatch, context: _FakeMainContext) -> None:
    """Install stub ``gi`` / ``gi.repository`` modules exposing ``GLib``."""
    glib = types.SimpleNamespace(
        MainContext=types.SimpleNamespace(default=lambda: context),
    )
    repository = types.ModuleType("gi.repository")
    repository.GLib = glib  # type: ignore[attr-defined]
    gi = types.ModuleType("gi")
    gi.repository = repository  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gi", gi)
    monkeypatch.setitem(sys.modules, "gi.repository", repository)


def test_glib_pump_skipped_for_threaded_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    """``xorg`` / ``win32`` run their own loop, so nothing is scheduled."""
    _fake_pystray(monkeypatch)
    clock = _RecordingClock()
    monkeypatch.setattr(runtime, "clock", clock)

    bridge = TrayPystrayBridge(TrayIcon(menu=[MenuEntry.quit()]))
    bridge.install()
    assert clock.scheduled == []

    bridge.uninstall()
    assert clock.unscheduled == []


def test_glib_pump_drains_context_for_appindicator(monkeypatch: pytest.MonkeyPatch) -> None:
    """The GTK-family backends get their GLib context iterated from the clock.

    Without this the initial ``_show()`` -- the D-Bus registration that makes
    the icon exist at all -- is queued and never dispatched (#647).
    """
    pystray = _fake_pystray(monkeypatch)
    monkeypatch.setattr(pystray.Icon, "__module__", "pystray._appindicator")
    context = _FakeMainContext(queued=3)
    _fake_glib(monkeypatch, context)
    clock = _RecordingClock()
    monkeypatch.setattr(runtime, "clock", clock)

    bridge = TrayPystrayBridge(TrayIcon(menu=[MenuEntry.quit()]))
    bridge.install()

    assert len(clock.scheduled) == 1
    pump = clock.scheduled[0]
    pump(0.016)
    assert context.iterations == 3  # everything ready this tick, then stop
    pump(0.016)
    assert context.iterations == 3  # an empty context is a cheap no-op

    bridge.uninstall()
    assert clock.unscheduled == [pump]
    context.queued = 2
    pump(0.016)  # detached from the context, so a late tick does nothing
    assert context.iterations == 3
