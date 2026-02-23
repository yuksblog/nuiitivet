from unittest.mock import patch, MagicMock

import pytest

from nuiitivet.material.text_fields import TextField
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.widgets.text_editing import TextRange
from nuiitivet.observable import Observable
from nuiitivet.input.codes import MOD_META, TEXT_MOTION_BACKSPACE
from nuiitivet.input.pointer import PointerEvent, PointerEventType


def test_text_field_value_property():
    tf = TextField(value="Hello")
    assert tf.value == "Hello"
    assert tf._editable._state_internal.value.text == "Hello"

    tf.value = "World"
    assert tf.value == "World"
    assert tf._editable._state_internal.value.text == "World"
    assert tf._editable._state_internal.value.selection.start == 5


def test_text_field_controlled_mode():
    obs = Observable("Initial")

    class VM:
        text = obs

    vm = VM()

    tf = TextField(value=vm.text)
    assert tf.value == "Initial"

    # Simulate external change
    vm.text.value = "Changed"
    # TextField subscribes on mount
    tf.mount(MagicMock())

    # Trigger subscription callback manually or wait if async (it's sync here)
    # But Observable subscription is immediate?
    # Wait, Observable.subscribe calls callback immediately? No.
    # But when value changes, it calls callback.

    vm.text.value = "Updated"
    assert tf.value == "Updated"


def test_text_field_input_handling():
    tf = TextField(value="")

    # Simulate text input
    tf._editable._handle_text("a")
    assert tf.value == "a"
    assert tf._editable._state_internal.value.selection.start == 1

    tf._editable._handle_text("b")
    assert tf.value == "ab"
    assert tf._editable._state_internal.value.selection.start == 2


def test_text_field_backspace():
    tf = TextField(value="abc")
    # Move cursor to end
    tf._editable._state_internal.value = tf._editable._state_internal.value.copy_with(selection=TextRange(3, 3))

    tf._editable._handle_text_motion(TEXT_MOTION_BACKSPACE)
    assert tf.value == "ab"

    tf._editable._handle_text_motion(TEXT_MOTION_BACKSPACE)
    assert tf.value == "a"


def test_text_field_selection_deletion():
    tf = TextField(value="abc")
    # Select "b"
    tf._editable._state_internal.value = tf._editable._state_internal.value.copy_with(selection=TextRange(1, 2))

    tf._editable._handle_text_motion(TEXT_MOTION_BACKSPACE)
    assert tf.value == "ac"


@patch("nuiitivet.widgets.editable_text.get_system_clipboard")
def test_copy(mock_get_clipboard):
    mock_clipboard = MagicMock()
    mock_get_clipboard.return_value = mock_clipboard

    tf = TextField(value="hello")
    # Select "ell"
    tf._editable._state_internal.value = tf._editable._state_internal.value.copy_with(selection=TextRange(1, 4))

    tf._editable._handle_key("c", MOD_META)

    mock_clipboard.set_text.assert_called_with("ell")


@patch("nuiitivet.widgets.editable_text.get_system_clipboard")
def test_paste(mock_get_clipboard):
    mock_clipboard = MagicMock()
    mock_clipboard.get_text.return_value = " world"
    mock_get_clipboard.return_value = mock_clipboard

    tf = TextField(value="hello")
    # Cursor at end
    tf._editable._state_internal.value = tf._editable._state_internal.value.copy_with(selection=TextRange(5, 5))

    tf._editable._handle_key("v", MOD_META)

    assert tf.value == "hello world"


def test_text_field_api_obscure_text_property_round_trip() -> None:
    tf = TextField(value="secret", obscure_text=True)
    assert tf.obscure_text is True

    tf.obscure_text = False
    assert tf.obscure_text is False


def test_text_field_api_rejects_icon_tap_callback_without_icon() -> None:
    with pytest.raises(ValueError):
        TextField(value="", on_tap_leading_icon=lambda: None)

    with pytest.raises(ValueError):
        TextField(value="", on_tap_trailing_icon=lambda: None)


def test_text_field_api_invokes_trailing_icon_callback_on_icon_press() -> None:
    tapped = False

    def _on_trailing() -> None:
        nonlocal tapped
        tapped = True

    tf = TextField(
        value="",
        trailing_icon="close",
        on_tap_trailing_icon=_on_trailing,
    )
    tf.layout(200, 56)

    tf._handle_press(PointerEvent.mouse_event(1, PointerEventType.PRESS, 187, 28))

    assert tapped is True


def test_text_field_api_supporting_text_and_is_error_color_contract() -> None:
    style = TextFieldStyle.outlined()
    tf = TextField(value="", supporting_text="hint", is_error=False, style=style)
    assert tf.supporting_text == "hint"
    assert tf.is_error is False
    assert tf._editable.cursor_color == style.cursor_color

    tf._set_is_error(True)
    assert tf.is_error is True
    assert tf._editable.cursor_color == style.error_cursor_color
