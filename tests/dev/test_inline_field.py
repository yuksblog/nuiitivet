"""The inline field's keys: several lines, broken by Shift+Enter, walked by the arrows."""

from __future__ import annotations

from nuiitivet.input.codes import MOD_SHIFT
from nuiitivet.dev import inline_field
from nuiitivet.dev.inline_field import InlineField
from nuiitivet.widgets.text_editing import TextRange


def _monospace(monkeypatch) -> None:
    monkeypatch.setattr(inline_field, "measure", lambda s: 10.0 * len(s))


def test_shift_enter_breaks_the_line_and_enter_commits() -> None:
    field = InlineField.open("ab")

    assert field.key("enter", MOD_SHIFT) is None
    field.type("cd")

    assert field.text == "ab\ncd"
    assert field.key("enter", 0) == "commit"


def test_typed_control_characters_never_break_the_line() -> None:
    field = InlineField.open("ab")

    field.type("\r")

    assert field.text == "ab"


def test_up_and_down_walk_the_lines_keeping_the_column(monkeypatch) -> None:
    _monospace(monkeypatch)
    field = InlineField.open("abcd\nef\nghij")
    field.value = field.value.copy_with(selection=TextRange(3, 3))

    field.key("down", 0)
    assert field.value.selection == TextRange(7, 7)
    field.key("down", 0)
    assert field.value.selection == TextRange(11, 11)
    field.key("up", MOD_SHIFT)
    assert field.value.selection == TextRange(11, 7)


def test_home_and_end_stop_at_the_line() -> None:
    field = InlineField.open("ab\ncd")
    field.value = field.value.copy_with(selection=TextRange(4, 4))

    field.key("home", 0)
    assert field.value.selection == TextRange(3, 3)
    field.key("end", 0)
    assert field.value.selection == TextRange(5, 5)


def test_a_paste_keeps_line_breaks_normalized(monkeypatch) -> None:
    class _Clipboard:
        def get_text(self) -> str:
            return "a\r\nb"

        def set_text(self, text: str) -> None:
            pass

    monkeypatch.setattr(inline_field, "get_system_clipboard", lambda: _Clipboard())
    monkeypatch.setattr(inline_field, "accel_held", lambda mods: True)
    field = InlineField.open("")

    field.key("v", 0)

    assert field.text == "a\nb"
