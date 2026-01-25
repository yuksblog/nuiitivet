from unittest.mock import patch, MagicMock
from nuiitivet.material.text_fields import TextField
from nuiitivet.widgets.text_editing import TextRange
from nuiitivet.observable import Observable
from nuiitivet.input.codes import MOD_META, TEXT_MOTION_BACKSPACE


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
