"""Tests for the App-level signals the dev bridge's ``status`` reads (#420):
the resolved ``title`` and the blank-frame probe (:meth:`App._frame_is_blank`).
"""

from __future__ import annotations

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.modifiers.background import background
from nuiitivet.observable.value import Observable
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting.widget import Widget


def test_title_returns_plain_string() -> None:
    app = App(Window(content=Container(width=10, height=10), title="Counter")).main_window
    assert app.title == "Counter"


def test_title_unwraps_observable() -> None:
    title: Observable[str | None] = Observable("Untitled")
    app = App(Window(content=Container(width=10, height=10), title=title)).main_window
    assert app.title == "Untitled"
    title.value = "Renamed"
    assert app.title == "Renamed"


def test_title_none_when_unset() -> None:
    app = App(Window(content=Container(width=10, height=10))).main_window
    assert app.title is None


def test_frame_is_blank_when_nothing_paints() -> None:
    pytest.importorskip("skia")
    # An empty layout-only container paints no pixels of its own, so the frame is
    # just the uniform background clear color -> blank.
    app = App(Window(content=Container(width=100, height=100), width=100, height=100)).main_window
    assert app._frame_is_blank() is True


def test_frame_is_not_blank_with_painted_content() -> None:
    pytest.importorskip("skia")
    # A colored box inset by padding leaves the background visible around it, so
    # the frame has more than one color -> not blank. (A box that filled the
    # whole frame would be a single uniform color and read as blank -- the
    # documented heuristic for an intentionally solid screen.)
    inner: Widget = Container().modifier(background((255, 0, 0, 255)))
    content: Widget = Container(child=inner, padding=20)
    app = App(Window(content=content, width=100, height=100)).main_window
    assert app._frame_is_blank() is False
