"""Tests for Window.hide()/show(), close_action, and the dock_visibility wiring.

Headless: no OS window exists, so visibility flips the model state only —
which is exactly the contract (the backend applies it when realized, and a
window hidden before realization starts hidden).
"""

from __future__ import annotations

import logging
from typing import List

import pytest

from nuiitivet.observable import Observable
from nuiitivet.platform.tray import TrayIcon
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting.widget import Widget


class _Root(Widget):
    pass


def test_close_action_validated() -> None:
    with pytest.raises(ValueError):
        Window(content=_Root(), close_action="minimize")
    Window(content=_Root(), close_action="hide")
    Window(content=_Root(), close_action=Observable("close"))


def test_hide_show_flip_visibility_without_os_window() -> None:
    app = App(Window(content=_Root()))
    window = app.main_window
    assert window.is_visible.value is True

    window.hide()
    assert window.is_visible.value is False
    assert window.is_open.value is True  # hidden is not closed

    window.show()
    assert window.is_visible.value is True

    window.close()
    window.show()  # a closed window is finished; show is a no-op
    assert window.is_open.value is False


def test_close_request_defaults_to_close() -> None:
    app = App(Window(content=_Root()))
    app.main_window._handle_close_request()
    assert app.main_window.is_open.value is False


def test_close_request_hide_parks_the_window_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = App(Window(content=_Root(), close_action="hide"))
    window = app.main_window
    with caplog.at_level(logging.WARNING):
        window._handle_close_request()
    assert window.is_open.value is True
    assert window.is_visible.value is False
    assert any("no way back" in message for message in caplog.messages)


def test_close_request_follows_observable() -> None:
    action = Observable("hide")
    app = App(Window(content=_Root(), close_action=action))
    window = app.main_window
    window._handle_close_request()
    assert window.is_open.value is True and window.is_visible.value is False

    window.show()
    action.value = "close"
    window._handle_close_request()
    assert window.is_open.value is False


def test_programmatic_close_ignores_close_action() -> None:
    app = App(Window(content=_Root(), close_action="hide"))
    app.main_window.close()
    assert app.main_window.is_open.value is False


def test_visible_window_count() -> None:
    app = App(Window(content=_Root()))
    assert app._visible_window_count() == 1
    app.main_window.hide()
    assert app._visible_window_count() == 0
    app.main_window.show()
    assert app._visible_window_count() == 1
    app.main_window.close()
    assert app._visible_window_count() == 0


class _DockBridge:
    def __init__(self) -> None:
        self.dock_calls: List[bool] = []

    def install(self) -> None:
        pass

    def uninstall(self) -> None:
        pass

    def set_dock_visible(self, visible: bool) -> None:
        self.dock_calls.append(visible)


def _dock_app(monkeypatch: pytest.MonkeyPatch, dock_visibility: str) -> tuple[App, _DockBridge]:
    bridge = _DockBridge()
    monkeypatch.setattr(TrayIcon, "_create_bridge", lambda self: bridge)
    tray = TrayIcon(dock_visibility=dock_visibility)
    app = App(Window(content=_Root()), tray=tray)
    app._install_tray()
    return app, bridge


def test_dock_auto_follows_window_visibility(monkeypatch: pytest.MonkeyPatch) -> None:
    app, bridge = _dock_app(monkeypatch, "auto")
    assert bridge.dock_calls == [True]  # initial refresh: one visible window
    app.main_window.hide()
    assert bridge.dock_calls == [True, False]
    app.main_window.show()
    assert bridge.dock_calls == [True, False, True]
    app.main_window.close()
    assert bridge.dock_calls == [True, False, True, False]


def test_dock_always_never_touched_by_visibility(monkeypatch: pytest.MonkeyPatch) -> None:
    app, bridge = _dock_app(monkeypatch, "always")
    app.main_window.hide()
    app.main_window.show()
    assert bridge.dock_calls == []


def test_hide_with_installed_tray_does_not_warn(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bridge = _DockBridge()
    monkeypatch.setattr(TrayIcon, "_create_bridge", lambda self: bridge)
    tray = TrayIcon()
    app = App(Window(content=_Root(), close_action="hide"), tray=tray)
    app._install_tray()
    assert tray.installed.value is True
    with caplog.at_level(logging.WARNING):
        app.main_window._handle_close_request()
    assert app.main_window.is_visible.value is False
    assert not any("no way back" in message for message in caplog.messages)
