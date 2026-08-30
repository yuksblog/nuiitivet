"""Tests for the Window operation methods and App theme methods."""

from unittest.mock import MagicMock, patch
import pytest
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.theme.plain_theme import PlainTheme
from nuiitivet.widgeting.widget import Widget


class MockWidget(Widget):
    def build(self):
        return self


@pytest.fixture
def app():
    root = MockWidget()
    app = App(Window(content=root))
    # Mock the backend window on the main window
    window = app.main_window
    window._window = MagicMock()
    window._window.screen = MagicMock()
    window._window.screen.width = 1920
    window._window.screen.height = 1080
    window._window.width = 800
    window._window.height = 600
    window._window.fullscreen = False
    return app


@patch("sys.platform", "linux")
def test_center_window(app):
    app.main_window.center()
    # (1920 - 800) // 2 = 560
    # (1080 - 600) // 2 = 240
    app.main_window._window.set_location.assert_called_once_with(560, 240)


@patch("sys.platform", "linux")
def test_maximize_window(app):
    app.main_window.maximize()
    app.main_window._window.maximize.assert_called_once()


@patch("sys.platform", "linux")
def test_minimize_window(app):
    app.main_window.minimize()
    app.main_window._window.minimize.assert_called_once()


@patch("sys.platform", "linux")
def test_restore_window(app):
    app.main_window._window.fullscreen = True
    app.main_window.restore()
    app.main_window._window.set_fullscreen.assert_called_once_with(False)


@patch("sys.platform", "linux")
def test_toggle_fullscreen(app):
    app.main_window._window.fullscreen = False
    app.main_window.full_screen()
    app.main_window._window.set_fullscreen.assert_called_once_with(True)


@patch("sys.platform", "linux")
def test_move_window(app):
    app.main_window.move_to(100, 200)
    app.main_window._window.set_location.assert_called_once_with(100, 200)


@patch("sys.platform", "linux")
def test_resize_window(app):
    app.main_window.resize(1024, 768)
    app.main_window._window.set_size.assert_called_once_with(1024, 768)


@patch("sys.platform", "linux")
def test_close_window(app):
    os_window = app.main_window._window
    app.main_window.close()
    os_window.close.assert_called_once()
    assert app.windows == ()


def test_set_theme_with_instance(app):
    theme = PlainTheme.dark()
    app.set_theme(theme)
    assert app._theme_manager.current is theme


def test_set_theme_by_registered_name(app):
    theme = PlainTheme.dark()
    app.register_themes({"midnight": theme})
    app.set_theme("midnight")
    assert app._theme_manager.current is theme


def test_set_theme_falls_back_to_builtins(app):
    app.set_theme("dark")
    assert app._theme_manager.current.mode == "dark"
    app.set_theme("light")
    assert app._theme_manager.current.mode == "light"
