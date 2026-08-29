"""Tests for the TrayIcon model: validation, install wiring, activation.

Platform bridges (Cocoa, pystray) are substituted; what is under test is the
model contract every platform shares — the ``installed`` observable, the
never-crash install policy, and the activation path.
"""

from __future__ import annotations

import logging
from typing import Any, List

import pytest

from nuiitivet.menus import MenuEntry
from nuiitivet.observable import Observable
from nuiitivet.platform.tray import TrayIcon
from nuiitivet.runtime.app import App
from nuiitivet.runtime.intents import ExitAppIntent
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting.widget import Widget


class _Root(Widget):
    pass


def _app(**kwargs: Any) -> App:
    return App(Window(content=_Root()), **kwargs)


class _FakeBridge:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: List[str] = []

    def install(self) -> None:
        if self.fail:
            raise RuntimeError("no tray host")
        self.calls.append("install")

    def uninstall(self) -> None:
        self.calls.append("uninstall")


def _wire(monkeypatch: pytest.MonkeyPatch, bridge: _FakeBridge) -> None:
    monkeypatch.setattr(TrayIcon, "_create_bridge", lambda self: bridge)


# ---- Model validation ------------------------------------------------------


def test_menu_rejects_non_items() -> None:
    with pytest.raises(TypeError):
        TrayIcon(menu=["Open"])  # type: ignore[list-item]


def test_dock_visibility_validated() -> None:
    for value in ("always", "auto", "never"):
        assert TrayIcon(dock_visibility=value).dock_visibility == value
    with pytest.raises(ValueError):
        TrayIcon(dock_visibility="sometimes")


def test_defaults() -> None:
    tray = TrayIcon()
    assert tray.menu == ()
    assert tray.icon_path is None
    assert tray.dock_visibility == "always"
    assert tray.installed.value is False


def test_app_rejects_non_tray() -> None:
    with pytest.raises(TypeError):
        _app(tray=object())  # type: ignore[arg-type]


# ---- Install wiring --------------------------------------------------------


def test_install_and_uninstall_flip_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _FakeBridge()
    _wire(monkeypatch, bridge)
    tray = TrayIcon()
    app = _app(tray=tray)
    assert app.tray is tray

    app._install_tray()
    assert tray.installed.value is True
    app._install_tray()  # second install is a no-op
    assert bridge.calls == ["install"]

    app._uninstall_tray()
    assert tray.installed.value is False
    assert bridge.calls == ["install", "uninstall"]


def test_install_failure_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _wire(monkeypatch, _FakeBridge(fail=True))
    tray = TrayIcon()
    app = _app(tray=tray)
    app._install_tray()  # must not propagate
    assert tray.installed.value is False
    app._uninstall_tray()  # nothing installed; still a no-op
    assert tray.installed.value is False


def test_app_without_tray_hooks_are_noops() -> None:
    app = _app()
    assert app.tray is None
    app._install_tray()
    app._uninstall_tray()


# ---- Activation ------------------------------------------------------------


def _installed_tray(
    monkeypatch: pytest.MonkeyPatch, app: App, **tray_kwargs: Any
) -> TrayIcon:
    tray = TrayIcon(**tray_kwargs)
    _wire(monkeypatch, _FakeBridge())
    tray._install(app)
    return tray


def test_activate_toggles_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    tray = _installed_tray(monkeypatch, _app())
    checked = Observable(False)
    item = MenuEntry("Wrap", on_select=lambda: None, checked=checked)
    tray._activate_item(item)
    assert checked.value is True


def test_activate_runs_on_select(monkeypatch: pytest.MonkeyPatch) -> None:
    tray = _installed_tray(monkeypatch, _app())
    record: List[str] = []
    tray._activate_item(MenuEntry("Open", on_select=lambda: record.append("open")))
    assert record == ["open"]


def test_activate_quit_dispatches_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app()
    dispatched: List[Any] = []
    monkeypatch.setattr(app, "dispatch", dispatched.append)
    tray = _installed_tray(monkeypatch, app)
    tray._activate_item(MenuEntry.quit())
    assert len(dispatched) == 1
    assert isinstance(dispatched[0], ExitAppIntent)


def test_activate_window_scoped_role_is_ignored(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    app = _app()
    dispatched: List[Any] = []
    monkeypatch.setattr(app, "dispatch", dispatched.append)
    tray = _installed_tray(monkeypatch, app)
    with caplog.at_level(logging.WARNING):
        tray._activate_item(MenuEntry.minimize())
    assert dispatched == []
    assert any("tray menu" in message for message in caplog.messages)


def test_fire_activate(monkeypatch: pytest.MonkeyPatch) -> None:
    record: List[str] = []
    tray = _installed_tray(monkeypatch, _app(), on_activate=lambda: record.append("hit"))
    tray._fire_activate()
    assert record == ["hit"]

    silent = _installed_tray(monkeypatch, _app())
    silent._fire_activate()  # no handler; a no-op
