"""The macOS text commands pyglet drops, raised as text motions.

The key tests hand a synthesized key-down to a ``PygletTextView`` that sits in
no window. AppKit itself turns the key into its commands, so a key bound to a
command the patch lacks fails here. They are skipped everywhere but darwin (CI
is Linux) and run in the local suite.
"""

from __future__ import annotations

import sys
from typing import Any

import pytest
from pyglet.window import key as pyglet_key

from nuiitivet.backends.pyglet import text_commands_macos
from nuiitivet.backends.pyglet.runner import _normalize_text_motion
from nuiitivet.input.codes import TEXT_MOTION_END, TEXT_MOTION_HOME, TEXT_MOTION_LEFT, TEXT_MOTION_RIGHT

macos_only = pytest.mark.skipif(sys.platform != "darwin", reason="AppKit text commands are macOS-only")

_MOTION = "on_text_motion"
_SELECT = "on_text_motion_select"


@pytest.mark.parametrize(
    "command, event, motion",
    [
        ("moveForward:", _MOTION, TEXT_MOTION_RIGHT),
        ("moveBackward:", _MOTION, TEXT_MOTION_LEFT),
        ("moveToBeginningOfParagraph:", _MOTION, TEXT_MOTION_HOME),
        ("moveToEndOfParagraph:", _MOTION, TEXT_MOTION_END),
        ("moveToLeftEndOfLine:", _MOTION, TEXT_MOTION_HOME),
        ("moveToRightEndOfLine:", _MOTION, TEXT_MOTION_END),
        ("moveForwardAndModifySelection:", _SELECT, TEXT_MOTION_RIGHT),
        ("moveBackwardAndModifySelection:", _SELECT, TEXT_MOTION_LEFT),
        ("moveToBeginningOfParagraphAndModifySelection:", _SELECT, TEXT_MOTION_HOME),
        ("moveToEndOfParagraphAndModifySelection:", _SELECT, TEXT_MOTION_END),
        ("moveToLeftEndOfLineAndModifySelection:", _SELECT, TEXT_MOTION_HOME),
        ("moveToRightEndOfLineAndModifySelection:", _SELECT, TEXT_MOTION_END),
    ],
)
def test_a_command_raises_the_motion_a_field_acts_on(command: str, event: str, motion: int) -> None:
    raised, pyglet_motion = text_commands_macos.COMMANDS[command]

    assert raised == event
    assert _normalize_text_motion(pyglet_motion) == motion


# --- real keys through AppKit ---------------------------------------------------

_SHIFT, _CTRL, _CMD = 1 << 17, 1 << 18, 1 << 20
# The flags AppKit sets on every arrow key: numeric pad and function.
_ARROW = (1 << 21) | (1 << 23)
_LEFT, _RIGHT = "", ""

_RIGHT_MOTION = pyglet_key.MOTION_RIGHT
_LEFT_MOTION = pyglet_key.MOTION_LEFT
_HOME_MOTION = pyglet_key.MOTION_BEGINNING_OF_LINE
_END_MOTION = pyglet_key.MOTION_END_OF_LINE


class _Window:
    """What a text view reads of its pyglet window, around one view."""

    def __init__(self) -> None:
        from pyglet.libs.darwin.cocoapy import ObjCClass

        self.events: list[tuple[Any, ...]] = []
        self._view = ObjCClass("PygletTextView").alloc().initWithCocoaWindow_(self)

    def dispatch_event(self, *event: Any) -> None:
        self.events.append(event)

    def key_down(self, flags: int, characters: str, plain: str, key_code: int, *, repeat: bool = False) -> None:
        """Have AppKit interpret one key-down, as pyglet's ``keyDown:`` does."""
        from pyglet.libs.darwin import cocoapy
        from pyglet.libs.darwin.cocoapy import ObjCClass

        make = ObjCClass("NSEvent").keyEventWithType_location_modifierFlags_timestamp_windowNumber_context_characters_charactersIgnoringModifiers_isARepeat_keyCode_  # noqa: E501
        key_down = 10
        event = make(
            key_down,
            cocoapy.NSPoint(0, 0),
            flags,
            0.0,
            0,
            None,
            cocoapy.CFSTR(characters),
            cocoapy.CFSTR(plain),
            repeat,
            key_code,
        )
        self._view.interpretKeyEvents_(ObjCClass("NSArray").arrayWithObject_(event))


@pytest.fixture
def window(monkeypatch: pytest.MonkeyPatch) -> _Window:
    import pyglet.window  # noqa: F401  (registers PygletTextView)

    monkeypatch.setattr(text_commands_macos, "_open_line_time", None)
    text_commands_macos.install_patch()
    return _Window()


@macos_only
@pytest.mark.parametrize(
    "flags, characters, plain, key_code, expected",
    [
        pytest.param(_CTRL, "\x06", "f", 3, (_MOTION, _RIGHT_MOTION), id="ctrl-f"),
        pytest.param(_CTRL, "\x02", "b", 11, (_MOTION, _LEFT_MOTION), id="ctrl-b"),
        pytest.param(_CTRL, "\x01", "a", 0, (_MOTION, _HOME_MOTION), id="ctrl-a"),
        pytest.param(_CTRL, "\x05", "e", 14, (_MOTION, _END_MOTION), id="ctrl-e"),
        pytest.param(_CMD | _ARROW, _LEFT, _LEFT, 123, (_MOTION, _HOME_MOTION), id="cmd-left"),
        pytest.param(_CMD | _ARROW, _RIGHT, _RIGHT, 124, (_MOTION, _END_MOTION), id="cmd-right"),
        pytest.param(_CTRL | _SHIFT, "\x06", "F", 3, (_SELECT, _RIGHT_MOTION), id="ctrl-shift-f"),
        pytest.param(_CTRL | _SHIFT, "\x02", "B", 11, (_SELECT, _LEFT_MOTION), id="ctrl-shift-b"),
        pytest.param(_CTRL | _SHIFT, "\x01", "A", 0, (_SELECT, _HOME_MOTION), id="ctrl-shift-a"),
        pytest.param(_CTRL | _SHIFT, "\x05", "E", 14, (_SELECT, _END_MOTION), id="ctrl-shift-e"),
        pytest.param(_CMD | _SHIFT | _ARROW, _LEFT, _LEFT, 123, (_SELECT, _HOME_MOTION), id="cmd-shift-left"),
        pytest.param(_CMD | _SHIFT | _ARROW, _RIGHT, _RIGHT, 124, (_SELECT, _END_MOTION), id="cmd-shift-right"),
    ],
)
def test_a_caret_key_raises_its_motion(
    window: _Window, flags: int, characters: str, plain: str, key_code: int, expected: tuple[str, int]
) -> None:
    window.key_down(flags, characters, plain, key_code)

    assert window.events == [expected]


@macos_only
def test_a_held_key_raises_its_motion_again(window: _Window) -> None:
    window.key_down(_CTRL, "\x06", "f", 3)
    window.key_down(_CTRL, "\x06", "f", 3, repeat=True)

    assert window.events == [(_MOTION, _RIGHT_MOTION)] * 2


@macos_only
def test_a_key_pyglet_forwards_raises_its_motion_once(window: _Window) -> None:
    window.key_down(_ARROW, _LEFT, _LEFT, 123)

    assert window.events == [(_MOTION, _LEFT_MOTION)]


@macos_only
def test_a_view_made_after_the_patch_raises_on_its_own_window(window: _Window) -> None:
    """A window that goes full screen gets a new view, which nothing registers."""
    later = _Window()

    later.key_down(_CTRL, "\x01", "a", 0)

    assert later.events == [(_MOTION, _HOME_MOTION)]
    assert window.events == []


@macos_only
def test_the_event_time_is_read_from_appkit() -> None:
    if sys.platform == "darwin":  # mypy on Linux does not see the darwin-only name
        time = text_commands_macos._event_time()

        assert time is None or isinstance(time, float)


@macos_only
def test_ctrl_o_does_not_walk_the_caret_back(window: _Window, monkeypatch: pytest.MonkeyPatch) -> None:
    """Its line break has no editing operation, so the move after it must not act alone."""
    monkeypatch.setattr(text_commands_macos, "_event_time", lambda: 1.0)

    window.key_down(_CTRL, "\x0f", "o", 31)

    assert window.events == []


@macos_only
def test_a_move_back_in_a_later_event_is_raised(window: _Window, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(text_commands_macos, "_event_time", lambda: 1.0)
    window.key_down(_CTRL, "\x0f", "o", 31)
    monkeypatch.setattr(text_commands_macos, "_event_time", lambda: 2.0)

    window.key_down(_CTRL, "\x02", "b", 11)

    assert window.events == [(_MOTION, _LEFT_MOTION)]
