from unittest.mock import MagicMock, patch

import pytest

from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.icon import Icon
from nuiitivet.widgets.text_editing import TextRange
from nuiitivet.observable import Observable
from nuiitivet.input.codes import (
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_LEFT,
)


def test_text_field_initial_value():
    tf = TextField(value="Hello")
    assert tf.value == "Hello"
    assert tf._editable._state_internal.value.selection == TextRange(5, 5)


def test_text_field_typing():
    tf = TextField(value="")
    tf._editable._handle_text("A")
    assert tf.value == "A"
    assert tf._editable._state_internal.value.selection == TextRange(1, 1)

    tf._editable._handle_text("B")
    assert tf.value == "AB"
    assert tf._editable._state_internal.value.selection == TextRange(2, 2)


def test_text_field_backspace():
    tf = TextField(value="AB")
    tf._editable._handle_text_motion(TEXT_MOTION_BACKSPACE)
    assert tf.value == "A"
    assert tf._editable._state_internal.value.selection == TextRange(1, 1)


def test_text_field_arrow_keys():
    tf = TextField(value="ABC")
    # Cursor at end (3)
    tf._editable._handle_text_motion(TEXT_MOTION_LEFT)
    assert tf._editable._state_internal.value.selection == TextRange(2, 2)


def test_text_field_paints_cursor_when_focused() -> None:
    tf = TextField(value="A", style=TextFieldStyle.outlined())
    tf._editable.state.focused = True

    mock_font = MagicMock()
    mock_font.measureText = MagicMock(return_value=10)
    mock_font.setSize = MagicMock()

    metrics = MagicMock()
    metrics.fAscent = -10
    metrics.fDescent = 3
    mock_font.getMetrics = MagicMock(return_value=metrics)

    canvas = MagicMock()

    with patch("nuiitivet.widgets.editable_text.EditableText._get_font", return_value=mock_font):
        with patch("nuiitivet.widgets.editable_text.make_paint", return_value=MagicMock()):
            with patch("nuiitivet.widgets.editable_text.resolve_color_to_rgba", return_value=(0, 0, 0, 255)):
                with patch("nuiitivet.widgets.editable_text.make_text_blob", return_value=None):
                    ime = MagicMock()
                    ime.update_cursor_rect = MagicMock()
                    with patch("nuiitivet.widgets.editable_text.IMEManager.get", return_value=ime):
                        tf._editable.paint(canvas, 0, 0, 200, 56)
    assert canvas.drawLine.called is True


def test_text_field_paints_editable_child() -> None:
    tf = TextField(value="Hello")
    tf.layout(200, 56)

    canvas = MagicMock()

    with patch.object(tf._editable, "paint", autospec=True) as paint_mock:
        tf.paint(canvas, 0, 0, 200, 56)

    assert paint_mock.called is True


def test_text_field_insertion_at_cursor():
    tf = TextField(value="AC")
    # Manually set cursor position for test
    current = tf._editable._state_internal.value
    tf._editable._state_internal.value = current.copy_with(selection=TextRange(1, 1))  # Cursor between A and C

    tf._editable._handle_text("B")
    assert tf.value == "ABC"
    assert tf._editable._state_internal.value.selection == TextRange(2, 2)


def _make_obs(initial):
    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def test_text_field_controlled():
    state = _make_obs("Start")

    def on_change(val):
        state.value = val

    tf = TextField(value=state, on_change=on_change)

    # Simulate mount to setup subscription
    tf.mount(MagicMock())

    assert tf.value == "Start"

    tf._editable._handle_text("!")
    assert state.value == "Start!"
    assert tf.value == "Start!"

    # Test external update
    state.value = "Reset"
    # The subscription should update internal state
    assert tf.value == "Reset"
    assert tf._editable._state_internal.value.selection == TextRange(5, 5)  # Cursor moved to end

    tf.on_unmount()


def test_text_field_observable_value_is_read_only_by_default() -> None:
    state = _make_obs("Start")
    tf = TextField(value=state)

    tf.mount(MagicMock())
    assert tf.value == "Start"

    tf._editable._handle_text("!")
    assert tf.value == "Start!"
    assert state.value == "Start"

    tf.on_unmount()


def test_text_field_bind_updates_observable() -> None:
    state = _make_obs("Start")
    tf = TextField.two_way(state)

    tf._editable._handle_text("!")
    assert tf.value == "Start!"
    assert state.value == "Start!"


def test_text_field_ime_composition():
    tf = TextField(value="")

    # Start composition "k"
    # handle_ime_composition(text, selection_start, selection_length)
    tf._editable._handle_ime_composition("k", 1, 0)
    assert tf.value == "k"
    assert tf._editable._state_internal.value.is_composing
    assert tf._editable._state_internal.value.composing == TextRange(0, 1)
    assert tf._editable._state_internal.value.selection == TextRange(1, 1)

    # Update composition "ka"
    tf._editable._handle_ime_composition("ka", 2, 0)
    assert tf.value == "ka"
    assert tf._editable._state_internal.value.composing == TextRange(0, 2)

    # Commit "ka" (usually on_text is called with the final string)
    # The OS usually calls insertText which triggers on_text.
    # Our _editable._handle_text logic should replace the composing range.
    tf._editable._handle_text("ka")
    assert tf.value == "ka"
    assert not tf._editable._state_internal.value.is_composing
    assert tf._editable._state_internal.value.selection == TextRange(2, 2)


def test_text_field_accepts_icon_sources_as_strings() -> None:
    tf = TextField(value="", leading_icon="search", trailing_icon="close")
    assert isinstance(tf.leading_icon, Icon)
    assert isinstance(tf.trailing_icon, Icon)


def test_text_field_rejects_widget_icon_instances() -> None:
    with pytest.raises(TypeError):
        TextField(value="", leading_icon=Icon("search"))  # type: ignore[arg-type]


def test_text_field_label_supports_observable() -> None:
    label = _make_obs("Name")
    tf = TextField(value="", label=label)

    tf.mount(MagicMock())
    assert tf.label == "Name"

    label.value = "Email"
    assert tf.label == "Email"

    tf.on_unmount()


def test_text_field_error_text_supports_observable_and_updates_cursor_color() -> None:
    error_text = _make_obs(None)
    style = TextFieldStyle.outlined()
    tf = TextField(value="", error_text=error_text, style=style)

    with patch.object(tf, "mark_needs_layout", wraps=tf.mark_needs_layout) as mark_needs_layout:
        tf.mount(MagicMock())
        assert tf.error_text is None
        assert tf._editable.cursor_color == style.cursor_color

        error_text.value = "Oops"
        assert tf.error_text == "Oops"
        assert tf._editable.cursor_color == style.error_cursor_color
        assert mark_needs_layout.called is True

    tf.on_unmount()


def test_text_field_disabled_supports_observable() -> None:
    disabled = _make_obs(False)
    tf = TextField(value="", disabled=disabled)

    tf.mount(MagicMock())
    assert tf.state.disabled is False
    assert tf._editable.state.disabled is False

    disabled.value = True
    assert tf.state.disabled is True
    assert tf._editable.state.disabled is True

    disabled.value = False
    assert tf.state.disabled is False
    assert tf._editable.state.disabled is False

    tf.on_unmount()
