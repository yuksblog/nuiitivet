"""``App(icon=...)``: the path the backends read the app icon from."""

from __future__ import annotations

from pathlib import Path

import pytest

import nuiitivet.material as nv
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgets.text import TextBase as Text


def _window() -> Window:
    return Window(content=lambda: Text("x"))


def test_the_icon_path_is_kept_as_a_path() -> None:
    assert App(_window(), icon="assets/app.png").icon_path == Path("assets/app.png")
    assert App(_window(), icon=Path("assets/app.png")).icon_path == Path("assets/app.png")


def test_no_icon_by_default() -> None:
    assert App(_window()).icon_path is None


def test_a_non_path_icon_is_refused() -> None:
    with pytest.raises(TypeError, match="App\\(icon=...\\)"):
        App(_window(), icon=42)  # type: ignore[arg-type]


def test_the_public_app_passes_the_icon_through() -> None:
    app = nv.App(nv.Window(content=lambda: nv.Text("x")), icon="assets/app.png")
    assert app.icon_path == Path("assets/app.png")
