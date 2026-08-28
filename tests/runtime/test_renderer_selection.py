"""Tests for renderer selection (App.run(renderer=...))."""

from unittest.mock import patch

import pytest

from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.runtime.renderer import (
    VALID_RENDERER_MODES,
    parse_renderer_mode,
)
from nuiitivet.widgeting.widget import Widget


class MockWidget(Widget):
    def build(self):
        return self


@pytest.fixture
def app():
    return App(Window(content=MockWidget()))


def test_valid_modes():
    assert VALID_RENDERER_MODES == ("auto", "gpu", "cpu")


@pytest.mark.parametrize("mode", ["auto", "gpu", "cpu"])
def test_parse_renderer_mode_accepts_valid(mode):
    assert parse_renderer_mode(mode) == mode


def test_parse_renderer_mode_rejects_unknown():
    with pytest.raises(ValueError):
        parse_renderer_mode("software")  # type: ignore[arg-type]


def test_run_defaults_to_auto(app):
    with patch("nuiitivet.backends.pyglet.runner.run_app") as run_app:
        app.run()
    run_app.assert_called_once()
    assert run_app.call_args.kwargs["renderer"] == "auto"


@pytest.mark.parametrize("mode", ["auto", "gpu", "cpu"])
def test_run_forwards_renderer(app, mode):
    with patch("nuiitivet.backends.pyglet.runner.run_app") as run_app:
        app.run(renderer=mode)
    assert run_app.call_args.kwargs["renderer"] == mode


def test_run_validates_renderer_before_launch(app):
    with patch("nuiitivet.backends.pyglet.runner.run_app") as run_app:
        with pytest.raises(ValueError):
            app.run(renderer="metal")  # type: ignore[arg-type]
    run_app.assert_not_called()
