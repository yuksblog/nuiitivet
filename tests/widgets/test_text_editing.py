"""Tests for the editing operations ``EditableText`` and the dev runner's inline field share."""

from __future__ import annotations

from nuiitivet.input.codes import (
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_LEFT,
    TEXT_MOTION_RIGHT,
)
from nuiitivet.widgets.text_editing import (
    TextEditingValue,
    TextRange,
    apply_motion,
    apply_shortcut,
    compose_text,
    end_composition,
    insert_text,
)


class _Clipboard:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text


def _at(text: str, caret: int) -> TextEditingValue:
    return TextEditingValue(text, TextRange(caret, caret))


# --- insertion -------------------------------------------------------------------


def test_insert_lands_at_the_caret_and_over_a_selection() -> None:
    assert insert_text(_at("ac", 1), "b") == _at("abc", 2)
    assert insert_text(TextEditingValue("abc", TextRange(3, 1)), "X") == _at("aX", 2)


def test_insert_drops_control_characters_and_reports_nothing_left() -> None:
    assert insert_text(_at("a", 1), "\r") is None
    assert insert_text(_at("a", 1), "b\tc") == _at("abc", 3)


def test_insert_replaces_the_composition_and_ends_it() -> None:
    composing = TextEditingValue("aかc", TextRange(2, 2), TextRange(1, 2))

    assert insert_text(composing, "火") == _at("a火c", 2)


def test_insert_runs_the_filter_over_before_and_after() -> None:
    seen: list[tuple[str, str]] = []

    def keep_old(old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        seen.append((old.text, new.text))
        return old

    assert insert_text(_at("a", 1), "b", filter=keep_old) == _at("a", 1)
    assert seen == [("a", "ab")]


# --- composition -----------------------------------------------------------------


def test_compose_opens_over_the_selection_then_updates_in_place() -> None:
    first = compose_text(TextEditingValue("abc", TextRange(1, 2)), "か", 0, 1)
    assert first == TextEditingValue("aかc", TextRange(1, 2), TextRange(1, 2))
    assert first is not None

    second = compose_text(first, "かん", 2, 0)
    assert second == TextEditingValue("aかんc", TextRange(3, 3), TextRange(1, 3))


def test_an_empty_composition_ends_it_and_is_nothing_without_one() -> None:
    open_ = TextEditingValue("aかc", TextRange(2, 2), TextRange(1, 2))

    assert compose_text(open_, "", 0, 0) == _at("ac", 1)
    assert compose_text(_at("ac", 1), "", 0, 0) is None


def test_end_composition_keeps_the_text() -> None:
    open_ = TextEditingValue("aかc", TextRange(2, 2), TextRange(1, 2))

    assert end_composition(open_) == TextEditingValue("aかc", TextRange(2, 2))
    assert end_composition(_at("ac", 1)) is None


# --- motions ---------------------------------------------------------------------


def test_backspace_and_delete_erase_one_character_or_the_selection() -> None:
    assert apply_motion(_at("abc", 2), TEXT_MOTION_BACKSPACE) == _at("ac", 1)
    assert apply_motion(_at("abc", 0), TEXT_MOTION_BACKSPACE) is None
    assert apply_motion(_at("abc", 1), TEXT_MOTION_DELETE) == _at("ac", 1)
    assert apply_motion(_at("abc", 3), TEXT_MOTION_DELETE) is None
    selected = TextEditingValue("abc", TextRange(3, 1))
    assert apply_motion(selected, TEXT_MOTION_BACKSPACE) == _at("a", 1)
    assert apply_motion(selected, TEXT_MOTION_DELETE) == _at("a", 1)


def test_arrows_move_the_caret_and_stop_at_the_ends() -> None:
    assert apply_motion(_at("abc", 1), TEXT_MOTION_LEFT) == _at("abc", 0)
    assert apply_motion(_at("abc", 0), TEXT_MOTION_LEFT) is None
    assert apply_motion(_at("abc", 2), TEXT_MOTION_RIGHT) == _at("abc", 3)
    assert apply_motion(_at("abc", 3), TEXT_MOTION_RIGHT) is None
    assert apply_motion(_at("abc", 2), TEXT_MOTION_HOME) == _at("abc", 0)
    assert apply_motion(_at("abc", 0), TEXT_MOTION_END) == _at("abc", 3)


def test_select_extends_from_the_anchor_and_an_unselecting_move_lands_on_the_near_edge() -> None:
    assert apply_motion(_at("abc", 1), TEXT_MOTION_RIGHT, select=True) == TextEditingValue("abc", TextRange(1, 2))
    assert apply_motion(_at("abc", 1), TEXT_MOTION_END, select=True) == TextEditingValue("abc", TextRange(1, 3))
    selected = TextEditingValue("abc", TextRange(1, 3))
    assert apply_motion(selected, TEXT_MOTION_LEFT) == _at("abc", 1)
    assert apply_motion(selected, TEXT_MOTION_RIGHT) == _at("abc", 3)


def test_an_unknown_motion_is_nothing() -> None:
    assert apply_motion(_at("abc", 1), 99) is None


# --- shortcuts -------------------------------------------------------------------


def test_select_all_copy_cut_and_paste() -> None:
    clipboard = _Clipboard()
    everything = apply_shortcut(_at("abc", 1), "a", clipboard)
    assert everything == TextEditingValue("abc", TextRange(0, 3))
    assert everything is not None

    assert apply_shortcut(everything, "c", clipboard) == everything and clipboard.text == "abc"
    assert apply_shortcut(everything, "x", clipboard) == _at("", 0)
    assert apply_shortcut(_at("z", 1), "v", clipboard) == _at("zabc", 4)


def test_copy_and_cut_leave_the_clipboard_alone_without_a_selection() -> None:
    clipboard = _Clipboard("kept")
    collapsed = _at("abc", 1)

    assert apply_shortcut(collapsed, "c", clipboard) == collapsed
    assert apply_shortcut(collapsed, "x", clipboard) == collapsed
    assert clipboard.text == "kept"


def test_an_empty_clipboard_pastes_nothing_and_a_paste_is_filtered() -> None:
    collapsed = _at("abc", 1)
    assert apply_shortcut(collapsed, "v", _Clipboard()) == collapsed

    def keep_old(old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        return old

    assert apply_shortcut(collapsed, "v", _Clipboard("X"), filter=keep_old) == collapsed


def test_a_key_that_is_not_a_shortcut_is_nothing() -> None:
    assert apply_shortcut(_at("abc", 1), "z", _Clipboard()) is None
