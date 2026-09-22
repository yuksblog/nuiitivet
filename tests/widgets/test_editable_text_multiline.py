"""Multi-line EditableText: line breaks, the caret across lines, sizing.

A fake font makes every character ten pixels wide and a line twelve tall, so
positions are exact without a skia backend.
"""

from __future__ import annotations

import pytest

from nuiitivet.input.codes import (
    MOD_META,
    MOD_SHIFT,
    TEXT_MOTION_DOWN,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_UP,
)
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.input_filter import deny
from nuiitivet.widgets.text_editing import TextRange


class _Metrics:
    fAscent = -10.0
    fDescent = 2.0


class _Font:
    def measureText(self, text: str) -> float:
        return 10.0 * len(text)

    def getMetrics(self) -> _Metrics:
        return _Metrics()


def _field(**kwargs) -> EditableText:
    w = EditableText(**kwargs)
    w._get_font = lambda: _Font()  # type: ignore[method-assign]
    return w


def _multiline(**kwargs) -> EditableText:
    return _field(multiline=True, **kwargs)


def _type(w: EditableText, text: str) -> None:
    for ch in text:
        w._handle_text(ch)


def _press(w: EditableText, x: float, y: float) -> None:
    w._handle_press(PointerEvent(id=1, type=PointerEventType.PRESS, x=x, y=y))


# --- the Enter key ----------------------------------------------------------------


def test_shift_enter_breaks_the_line() -> None:
    w = _multiline()
    _type(w, "ab")

    assert w._handle_key("enter", MOD_SHIFT) is True
    _type(w, "cd")

    assert w.value == "ab\ncd"
    assert w._state_internal.value.selection == TextRange(5, 5)


def test_a_bare_enter_is_left_to_a_shortcut_when_there_is_nothing_to_submit_to() -> None:
    w = _multiline(max_lines=3)
    _type(w, "ab")

    assert w._handle_key("enter", 0) is False

    assert w.value == "ab"


def test_enter_submits_when_there_is_and_shift_enter_still_breaks() -> None:
    seen: list[str] = []
    w = _multiline(on_submit=seen.append)
    _type(w, "ab")

    w._handle_key("enter", MOD_SHIFT)
    w._handle_key("enter", 0)

    assert seen == ["ab\n"]
    assert w.value == "ab\n"


def test_a_single_line_field_never_breaks_the_line() -> None:
    w = _field()
    _type(w, "ab")

    assert w._handle_key("enter", MOD_SHIFT) is False
    assert w._handle_key("enter", 0) is False
    assert w.value == "ab"


def test_shift_enter_never_submits_even_in_a_single_line_field() -> None:
    seen: list[str] = []
    w = _field(on_submit=seen.append)
    _type(w, "ab")

    assert w._handle_key("enter", MOD_SHIFT) is False
    assert seen == []
    assert w._handle_key("enter", 0) is True
    assert seen == ["ab"]


def test_the_enter_confirming_a_composition_breaks_nothing() -> None:
    w = _multiline()
    w._handle_ime_composition("あ", 1, 0)
    w._handle_text("あ")

    assert w._handle_key("enter", 0) is False
    assert w.value == "あ"


def test_typed_control_characters_never_become_a_line_break() -> None:
    w = _multiline()
    _type(w, "ab")

    # macOS delivers Return as on_text('\r') beside the key press; the key is the break.
    assert w._handle_text("\r") is False
    assert w._handle_text("\n") is False
    assert w.value == "ab"


def test_the_input_filter_sees_the_line_break() -> None:
    w = _multiline(input_filter=deny(r"\s"))
    _type(w, "ab")

    w._handle_key("enter", MOD_SHIFT)

    assert w.value == "ab"


# --- paste ------------------------------------------------------------------------


class _Clipboard:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text


def test_a_paste_keeps_line_breaks_in_a_multi_line_field_and_normalizes_them(monkeypatch) -> None:
    monkeypatch.setattr("nuiitivet.widgets.editable_text.get_system_clipboard", lambda: _Clipboard("a\r\nb\rc\n"))
    w = _multiline()

    assert w._handle_key("v", MOD_META) is True

    assert w.value == "a\nb\nc\n"


def test_a_paste_drops_line_breaks_in_a_single_line_field(monkeypatch) -> None:
    monkeypatch.setattr("nuiitivet.widgets.editable_text.get_system_clipboard", lambda: _Clipboard("a\r\nb\rc"))
    w = _field()

    w._handle_key("v", MOD_META)

    assert w.value == "abc"


# --- the caret across lines -------------------------------------------------------


def test_up_and_down_move_between_lines_keeping_the_column() -> None:
    w = _multiline(value="abcd\nef\nghij")
    w.layout(200, 100)
    w._state_internal.value = w._state_internal.value.copy_with(selection=TextRange(3, 3))

    assert w._handle_text_motion(TEXT_MOTION_DOWN) is True
    assert w._state_internal.value.selection == TextRange(7, 7)
    assert w._handle_text_motion(TEXT_MOTION_DOWN) is True
    assert w._state_internal.value.selection == TextRange(11, 11), "the short line did not lose the column"
    assert w._handle_text_motion(TEXT_MOTION_UP) is True
    assert w._state_internal.value.selection == TextRange(7, 7)


def test_typing_drops_the_remembered_column() -> None:
    w = _multiline(value="abcd\nef\nghij")
    w.layout(200, 100)
    w._state_internal.value = w._state_internal.value.copy_with(selection=TextRange(3, 3))

    w._handle_text_motion(TEXT_MOTION_DOWN)
    w._handle_text("x")
    w._handle_text_motion(TEXT_MOTION_DOWN)

    assert w._state_internal.value.selection == TextRange(12, 12), "the column is where the typing left it"


def test_up_and_down_do_nothing_in_a_single_line_field() -> None:
    w = _field(value="ab")

    assert w._handle_text_motion(TEXT_MOTION_UP) is False
    assert w._handle_text_motion(TEXT_MOTION_DOWN) is False


def test_home_and_end_stop_at_the_wrapped_line() -> None:
    w = _multiline(value="hello world")
    w.layout(50, 100)
    w._state_internal.value = w._state_internal.value.copy_with(selection=TextRange(8, 8))

    w._handle_text_motion(TEXT_MOTION_HOME)
    assert w._state_internal.value.selection == TextRange(6, 6)
    w._handle_text_motion(TEXT_MOTION_END, select=True)
    assert w._state_internal.value.selection == TextRange(6, 11)


def test_shift_down_selects_across_lines() -> None:
    w = _multiline(value="ab\ncd")
    w.layout(200, 100)
    w._state_internal.value = w._state_internal.value.copy_with(selection=TextRange(1, 1))

    w._handle_text_motion(TEXT_MOTION_DOWN, select=True)

    assert w._state_internal.value.selection == TextRange(1, 4)


# --- pointing ---------------------------------------------------------------------


def test_a_press_lands_on_the_line_under_the_pointer() -> None:
    w = _multiline(value="ab\ncd\nef")
    w.layout(200, 100)

    _press(w, 14.0, 15.0)

    assert w._state_internal.value.selection == TextRange(4, 4)


def test_a_press_below_the_last_line_lands_on_it() -> None:
    w = _multiline(value="ab\ncd")
    w.layout(200, 100)

    _press(w, 99.0, 90.0)

    assert w._state_internal.value.selection == TextRange(5, 5)


def test_a_press_on_a_wrapped_line_uses_the_wrap_width() -> None:
    w = _multiline(value="hello world")
    w.layout(50, 100)

    _press(w, 0.0, 15.0)

    assert w._state_internal.value.selection == TextRange(6, 6)


# --- sizing -----------------------------------------------------------------------


def test_the_field_is_min_lines_tall_when_empty_and_grows_a_line_at_a_time() -> None:
    w = _multiline(min_lines=2)
    assert w.preferred_size() == (0, 24)

    w.value = "a\nb\nc"
    assert w.preferred_size() == (10, 36)


def test_max_lines_caps_the_height() -> None:
    w = _multiline(max_lines=3, value="a\nb\nc\nd\ne")
    assert w.preferred_size() == (10, 36)
    assert w.line_count() == 5


def test_wrapping_counts_toward_the_lines() -> None:
    w = _multiline(value="hello world")
    assert w.line_count(50) == 2
    assert w.preferred_size(max_width=50) == (60, 24)


def test_a_single_line_field_stays_one_line_tall() -> None:
    w = _field(value="a\nb")
    assert w.line_count() == 1
    assert w.preferred_size() == (30, 12)


def test_the_line_bounds_are_checked() -> None:
    with pytest.raises(ValueError):
        EditableText(multiline=True, min_lines=0)
    with pytest.raises(ValueError):
        EditableText(multiline=True, min_lines=3, max_lines=2)


def test_set_lines_switches_the_mode_after_construction() -> None:
    w = _field(value="a\nb")
    assert w.multiline is False

    w.set_lines(True, 2, 4)

    assert (w.multiline, w.min_lines, w.max_lines) == (True, 2, 4)
    assert w.line_count() == 2
