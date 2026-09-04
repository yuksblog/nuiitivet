"""Tests for the pyglet runner's mouse button/modifier normalization.

These exercise the runner's raw-pyglet -> backend-neutral mapping directly; the
end-to-end dispatch of the normalized values is covered in
``tests/runtime/test_mouse_button_dispatch.py``.
"""

import pyglet.window.key as pygkey
import pyglet.window.mouse as pygmouse

from nuiitivet.backends.pyglet import runner
from nuiitivet.input.codes import (
    BUTTON_LEFT,
    BUTTON_MIDDLE,
    BUTTON_RIGHT,
    MOD_CTRL,
    MOD_SHIFT,
)


def test_normalize_mouse_button_maps_known_buttons():
    assert runner._normalize_mouse_button(pygmouse.LEFT) == BUTTON_LEFT
    assert runner._normalize_mouse_button(pygmouse.MIDDLE) == BUTTON_MIDDLE
    assert runner._normalize_mouse_button(pygmouse.RIGHT) == BUTTON_RIGHT


def test_normalize_mouse_button_unknown_is_none():
    # An unrecognized raw value must not leak through as a button.
    assert runner._normalize_mouse_button(1 << 20) is None


def test_normalize_mouse_buttons_bitmask():
    assert runner._normalize_mouse_buttons(0) == 0
    assert runner._normalize_mouse_buttons(pygmouse.LEFT) == BUTTON_LEFT
    combined = pygmouse.LEFT | pygmouse.RIGHT
    assert runner._normalize_mouse_buttons(combined) == (BUTTON_LEFT | BUTTON_RIGHT)


def test_normalize_modifiers_maps_bits():
    assert runner._normalize_modifiers(pygkey.MOD_SHIFT) == MOD_SHIFT
    both = pygkey.MOD_SHIFT | pygkey.MOD_CTRL
    assert runner._normalize_modifiers(both) == (MOD_SHIFT | MOD_CTRL)
