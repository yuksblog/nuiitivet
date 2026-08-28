"""Tests for intent dispatch scoping: App vs Window."""

from unittest.mock import MagicMock, patch
import pytest
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.runtime.intents import ExitAppIntent
from nuiitivet.runtime.window_intents import (
    CenterWindowIntent,
    CloseWindowIntent,
    FullScreenIntent,
    MaximizeWindowIntent,
    MinimizeWindowIntent,
    MoveWindowIntent,
    ResizeWindowIntent,
    RestoreWindowIntent,
)
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


def test_dispatch_exit_app(app):
    with patch.object(app, "exit") as mock_exit:
        app.dispatch(ExitAppIntent(exit_code=123))
        mock_exit.assert_called_once_with(123)


@patch("sys.platform", "linux")
def test_dispatch_center_window(app):
    app.main_window.dispatch(CenterWindowIntent())
    # (1920 - 800) // 2 = 560
    # (1080 - 600) // 2 = 240
    app.main_window._window.set_location.assert_called_once_with(560, 240)


@patch("sys.platform", "linux")
def test_dispatch_maximize_window(app):
    app.main_window.dispatch(MaximizeWindowIntent())
    app.main_window._window.maximize.assert_called_once()


@patch("sys.platform", "linux")
def test_dispatch_minimize_window(app):
    app.main_window.dispatch(MinimizeWindowIntent())
    app.main_window._window.minimize.assert_called_once()


@patch("sys.platform", "linux")
def test_dispatch_restore_window(app):
    app.main_window._window.fullscreen = True
    app.main_window.dispatch(RestoreWindowIntent())
    app.main_window._window.set_fullscreen.assert_called_once_with(False)


@patch("sys.platform", "linux")
def test_dispatch_toggle_fullscreen(app):
    app.main_window._window.fullscreen = False
    app.main_window.dispatch(FullScreenIntent())
    app.main_window._window.set_fullscreen.assert_called_once_with(True)


@patch("sys.platform", "linux")
def test_dispatch_move_window(app):
    app.main_window.dispatch(MoveWindowIntent(x=100, y=200))
    app.main_window._window.set_location.assert_called_once_with(100, 200)


@patch("sys.platform", "linux")
def test_dispatch_resize_window(app):
    app.main_window.dispatch(ResizeWindowIntent(width=1024, height=768))
    app.main_window._window.set_size.assert_called_once_with(1024, 768)


@patch("sys.platform", "linux")
def test_dispatch_close_window(app):
    os_window = app.main_window._window
    app.main_window.dispatch(CloseWindowIntent())
    os_window.close.assert_called_once()
    assert app.windows == ()


def test_app_rejects_window_scoped_intent(app):
    with pytest.raises(TypeError, match="window-scoped"):
        app.dispatch(CloseWindowIntent())


def test_window_rejects_app_scoped_intent(app):
    with pytest.raises(TypeError, match="App.of"):
        app.main_window.dispatch(ExitAppIntent())
