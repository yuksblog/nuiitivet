"""Tests for the translation of browser input into the framework's codes."""

import pytest

from nuiitivet.backends.web.input import button_code, buttons_mask, key_name, wheel_steps
from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT


def test_button_follows_the_browser_numbering() -> None:
    assert [button_code(n) for n in (0, 1, 2)] == [BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT]
    assert button_code(3) is None


def test_held_buttons_swap_right_and_middle() -> None:
    assert buttons_mask(0) == 0
    assert buttons_mask(2) == BUTTON_RIGHT
    assert buttons_mask(4) == BUTTON_MIDDLE
    assert buttons_mask(1 | 2 | 4) == BUTTON_LEFT | BUTTON_MIDDLE | BUTTON_RIGHT


def test_a_pixel_delta_scrolls_that_many_pixels_at_the_default_multiplier() -> None:
    from nuiitivet.scrolling import ScrollController

    assert wheel_steps(100.0, 0) * ScrollController().scroll_multiplier == 100.0


def test_a_line_delta_is_one_step_per_line() -> None:
    assert wheel_steps(-3.0, 1) == -3.0


@pytest.mark.parametrize(
    ("key", "code", "name"),
    [
        ("a", "KeyA", "a"),
        ("A", "KeyA", "a"),
        (" ", "Space", "space"),
        ("Enter", "Enter", "enter"),
        ("Tab", "Tab", "tab"),
        ("Escape", "Escape", "escape"),
        ("ArrowLeft", "ArrowLeft", "left"),
        ("PageUp", "PageUp", "pageup"),
        ("!", "Digit1", "1"),
        ("F5", "F5", "f5"),
    ],
)
def test_key_names(key: str, code: str, name: str) -> None:
    assert key_name(key, code) == name
