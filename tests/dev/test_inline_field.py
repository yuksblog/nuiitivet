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


# --- where the field hangs ------------------------------------------------------


def test_a_slot_under_a_rect_extends_right_from_its_left_edge_with_a_gap() -> None:
    slot = inline_field.Slot.under((100.0, 50.0, 40.0, 20.0), (180.0, 24.0), 6.0, (600.0, 400.0))

    assert slot.side == "right" and slot.anchor == (100.0, 76.0)
    assert slot.room == 600.0 - 12.0 - 100.0
    assert slot.place((180.0, 24.0), (600.0, 400.0)) == (100.0, 76.0)


def test_the_room_never_falls_under_the_least_width() -> None:
    slot = inline_field.Slot.under((20.0, 50.0, 40.0, 20.0), (180.0, 24.0), 6.0, (100.0, 400.0))

    assert slot.room == 180.0


def test_a_box_is_pushed_inside_the_margins() -> None:
    slot = inline_field.Slot.under((500.0, 370.0, 40.0, 20.0), (180.0, 24.0), 6.0, (600.0, 400.0))

    assert slot.place((180.0, 72.0), (600.0, 400.0)) == (600.0 - 12.0 - 180.0, 400.0 - 12.0 - 72.0)


def test_a_slot_over_a_widget_extends_right_from_its_left_edge() -> None:
    slot = inline_field.Slot.over((250.0, 30.0, 100.0, 40.0), (300.0, 200.0))

    assert slot.side == "right" and slot.least == (100.0, 40.0)
    assert slot.room == 100.0, "the widget is wider than the room left, so the least width wins"
    assert slot.place((100.0, 40.0), (300.0, 200.0)) == (300.0 - 12.0 - 100.0, 30.0)


def test_up_and_down_walk_the_wrapped_lines(monkeypatch) -> None:
    _monospace(monkeypatch)
    field = InlineField.open("ab cd ef", wrap=50.0)
    field.value = field.value.copy_with(selection=TextRange(0, 0))

    field.key("down", 0)

    assert field.value.selection == TextRange(6, 6), "the second line starts where the first wrapped"
