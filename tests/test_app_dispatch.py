"""Tests for App.dispatch handling of intents."""

from unittest.mock import MagicMock, patch
import pytest
from nuiitivet.runtime.app import App
from nuiitivet.runtime.intents import (
    ExitAppIntent,
    CenterWindowIntent,
    MaximizeWindowIntent,
    MinimizeWindowIntent,
    RestoreWindowIntent,
    FullScreenIntent,
    CloseWindowIntent,
    MoveWindowIntent,
    ResizeWindowIntent,
)
from nuiitivet.widgeting.widget import Widget


class MockWidget(Widget):
    def build(self):
        return self


@pytest.fixture
def app():
    root = MockWidget()
    app = App(content=root)
    # Mock the window
    app._window = MagicMock()
    app._window.screen = MagicMock()
    app._window.screen.width = 1920
    app._window.screen.height = 1080
    app._window.width = 800
    app._window.height = 600
    app._window.fullscreen = False
    return app


def test_dispatch_exit_app(app):
    with patch.object(app, "exit") as mock_exit:
        app.dispatch(ExitAppIntent(exit_code=123))
        mock_exit.assert_called_once_with(123)


@patch("sys.platform", "linux")
def test_dispatch_center_window(app):
    app.dispatch(CenterWindowIntent())
    # (1920 - 800) // 2 = 560
    # (1080 - 600) // 2 = 240
    app._window.set_location.assert_called_once_with(560, 240)


@patch("sys.platform", "linux")
def test_dispatch_maximize_window(app):
    app.dispatch(MaximizeWindowIntent())
    app._window.maximize.assert_called_once()


@patch("sys.platform", "linux")
def test_dispatch_minimize_window(app):
    app.dispatch(MinimizeWindowIntent())
    app._window.minimize.assert_called_once()


@patch("sys.platform", "linux")
def test_dispatch_restore_window(app):
    app._window.fullscreen = True
    app.dispatch(RestoreWindowIntent())
    app._window.set_fullscreen.assert_called_once_with(False)


@patch("sys.platform", "linux")
def test_dispatch_toggle_fullscreen(app):
    app._window.fullscreen = False
    app.dispatch(FullScreenIntent())
    app._window.set_fullscreen.assert_called_once_with(True)


@patch("sys.platform", "linux")
def test_dispatch_move_window(app):
    app.dispatch(MoveWindowIntent(x=100, y=200))
    app._window.set_location.assert_called_once_with(100, 200)


@patch("sys.platform", "linux")
def test_dispatch_resize_window(app):
    app.dispatch(ResizeWindowIntent(width=1024, height=768))
    app._window.set_size.assert_called_once_with(1024, 768)


@patch("sys.platform", "linux")
def test_dispatch_close_window(app):
    app.dispatch(CloseWindowIntent())
    app._window.close.assert_called_once()
