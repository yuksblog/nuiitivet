"""Every cursor shape has a native cursor on each backend."""

import pyglet

from nuiitivet.backends.pyglet.runner import PYGLET_CURSOR_NAMES
from nuiitivet.backends.web.input import CSS_CURSOR_NAMES, cursor_css
from nuiitivet.input.cursor import MouseCursor


def test_every_shape_has_a_pyglet_system_cursor() -> None:
    window_cls = pyglet.window.Window
    system_cursors = {getattr(window_cls, name) for name in dir(window_cls) if name.startswith("CURSOR_")}
    for shape in MouseCursor:
        assert PYGLET_CURSOR_NAMES[shape] in system_cursors


def test_every_shape_has_a_css_cursor() -> None:
    for shape in MouseCursor:
        assert cursor_css(shape) == CSS_CURSOR_NAMES[shape]
        assert cursor_css(shape)


def test_the_hand_and_the_i_beam_are_the_browser_names() -> None:
    assert cursor_css(MouseCursor.POINTER) == "pointer"
    assert cursor_css(MouseCursor.TEXT) == "text"
    assert cursor_css(MouseCursor.DEFAULT) == "default"
