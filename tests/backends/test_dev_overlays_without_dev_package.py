"""A frozen app leaves out ``nuiitivet.dev``: the dev overlays paint nothing and log nothing."""

from __future__ import annotations

import logging
import sys
from types import SimpleNamespace

import pytest

from nuiitivet.backends.pyglet import gpu_frame
from nuiitivet.runtime.window import Window


@pytest.fixture
def no_dev_package(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [name for name in sys.modules if name == "nuiitivet.dev" or name.startswith("nuiitivet.dev.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "nuiitivet.dev", None)


@pytest.mark.usefixtures("no_dev_package")
def test_gpu_frame_overlays_are_silent_without_the_dev_package(caplog: pytest.LogCaptureFixture) -> None:
    app = SimpleNamespace(width=100, height=100)
    with caplog.at_level(logging.DEBUG):
        gpu_frame._paint_dev_action_overlay(app, object())
        gpu_frame._paint_dev_comment_overlay(app, object())
    assert caplog.records == []


@pytest.mark.usefixtures("no_dev_package")
def test_window_overlays_are_silent_without_the_dev_package(caplog: pytest.LogCaptureFixture) -> None:
    window = SimpleNamespace(width=100, height=100)
    with caplog.at_level(logging.DEBUG):
        Window._paint_dev_overlays(window, object())  # type: ignore[arg-type]
    assert caplog.records == []
