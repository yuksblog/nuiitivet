"""``TextField.multiline``: its height follows the lines, its first row stays a single-line field."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nuiitivet.input.codes import MOD_SHIFT
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.text_fields import TextField


class _Metrics:
    fAscent = -10.0
    fDescent = 2.0


class _Font:
    def measureText(self, text: str) -> float:
        return 10.0 * len(text)

    def getMetrics(self) -> _Metrics:
        return _Metrics()

    def setSize(self, size: float) -> None:
        pass


def _fake_font(tf: TextField) -> TextField:
    tf._get_font = lambda: _Font()  # type: ignore[method-assign]
    tf._editable._get_font = lambda: _Font()  # type: ignore[method-assign]
    return tf


def _single(**kwargs) -> TextField:
    return _fake_font(TextField(**kwargs))


def _multi(**kwargs) -> TextField:
    return _fake_font(TextField.multiline(**kwargs))


def test_the_constructor_switches_the_editable_and_the_options_reach_it() -> None:
    tf = TextField.multiline(min_lines=2, max_lines=4)

    assert (tf.is_multiline, tf.min_lines, tf.max_lines) == (True, 2, 4)
    assert (tf._editable.multiline, tf._editable.min_lines, tf._editable.max_lines) == (True, 2, 4)
    assert TextField().is_multiline is False


def test_the_constructor_forwards_the_rest_of_the_field() -> None:
    seen: list[str] = []
    tf = TextField.multiline("note", label="Notes", on_submit=seen.append, width=320, key="notes")

    assert (tf.value, tf.label, tf.key) == ("note", "Notes", "notes")
    tf._editable._handle_key("enter", 0)
    assert seen == ["note"]


def test_an_empty_field_is_one_row_tall_and_min_lines_adds_rows() -> None:
    assert _multi(width=200).preferred_size()[1] == 56
    assert _multi(min_lines=3, width=200).preferred_size()[1] == 56 + 2 * 12


def test_the_field_grows_with_the_text_up_to_max_lines() -> None:
    tf = _multi(max_lines=3, width=200)
    assert tf.preferred_size()[1] == 56

    tf.value = "a\nb"
    assert tf.preferred_size()[1] == 56 + 12

    tf.value = "a\nb\nc\nd\ne"
    assert tf.preferred_size()[1] == 56 + 2 * 12


def test_wrapping_at_the_width_grows_the_field_too() -> None:
    # 200 wide, 16 of inset each side: 168 for the text, seventeen characters.
    tf = _multi(width=200, value="a" * 20)
    assert tf.preferred_size()[1] == 56 + 12


def test_a_single_line_field_is_unmoved_by_line_breaks_in_its_value() -> None:
    assert _single(width=200, value="a\nb\nc").preferred_size()[1] == 56


def test_a_typed_line_break_asks_for_a_relayout() -> None:
    tf = _multi(width=200)
    tf.mark_needs_layout = MagicMock()  # type: ignore[method-assign]
    tf._editable.mark_needs_layout = MagicMock()  # type: ignore[method-assign]

    tf._editable._handle_text("a")
    tf._editable._handle_key("enter", MOD_SHIFT)

    assert tf._editable.mark_needs_layout.called


def test_the_first_line_sits_where_a_single_line_would() -> None:
    single = _single(width=200, style=TextFieldStyle.outlined())
    single.layout(200, 56)
    multi = _multi(width=200, style=TextFieldStyle.outlined(), value="a\nb")
    multi.layout(200, 68)

    single_rect = single._editable.layout_rect
    multi_rect = multi._editable.layout_rect
    assert single_rect is not None and multi_rect is not None
    # Single: text is centred in the 24 tall text area, so its top is 16 + 6.
    assert multi_rect[1] == single_rect[1] + (single_rect[3] - 12) // 2
    assert multi_rect[3] == 68 - multi_rect[1] - 16


def _label_y(tf: TextField, y: int, height: int) -> float:
    tf.layout(200, height)
    canvas = MagicMock()
    with patch("nuiitivet.material.text_fields.make_text_blob", return_value=MagicMock()):
        with patch("nuiitivet.material.text_fields.make_paint", return_value=MagicMock()):
            tf._draw_label(canvas, 16, y + 16, height - 32, y)
    return canvas.drawTextBlob.call_args[0][2]


def test_the_resting_label_follows_the_field_wherever_it_is_painted() -> None:
    single = _single(width=200, label="Name", style=TextFieldStyle.outlined())
    multi = _multi(min_lines=3, width=200, label="Name", style=TextFieldStyle.outlined())

    at_origin = _label_y(single, 0, 56)
    lower = _label_y(single, 100, 56)
    assert lower == at_origin + 100
    assert 0 < at_origin < 56
    # The multi-line field rests its label in the first row, not mid-field.
    assert _label_y(multi, 0, 80) == at_origin


def test_icons_stay_in_the_first_row() -> None:
    tf = _multi(width=240, leading_icon="person", value="a\nb\nc")
    tf.layout(240, 80)

    assert tf.leading_icon is not None and tf.leading_icon.layout_rect is not None
    icon_h = tf.leading_icon.layout_rect[3]
    assert tf.leading_icon.layout_rect[1] == (56 - icon_h) // 2
