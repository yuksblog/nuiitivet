from unittest.mock import patch, MagicMock

import pytest

from nuiitivet.material.text_fields import TextField
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.buttons import IconButton
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.text_editing import TextRange
from nuiitivet.observable import Observable
from nuiitivet.widgets.input_filter import digits_only, max_length
from nuiitivet.input.codes import MOD_META, TEXT_MOTION_BACKSPACE
from nuiitivet.input.pointer import PointerEventType

from tests.helpers.pointer import send_pointer_event_for_test_via_app_routing


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


def test_text_field_on_submit_fires_with_confirmed_value():
    seen: list[str] = []
    tf = TextField(value="", on_submit=seen.append)

    for ch in "search":
        tf._editable._handle_text(ch)
    tf._editable._handle_key("enter", 0)

    assert seen == ["search"]
    # Enter must not alter the value (issue #307).
    assert tf.value == "search"


def test_text_field_on_submit_omitted_is_noop():
    tf = TextField(value="hi")
    # No on_submit configured: Enter is harmless and leaves the value intact.
    tf._editable._handle_key("enter", 0)
    assert tf.value == "hi"


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
    root = Box()
    root.add_child(tf)
    root.layout(250, 106)
    root.set_layout_rect(0, 0, 250, 106)
    root.set_last_rect(0, 0, 250, 106)
    tf.layout(200, 56)
    tf.set_layout_rect(0, 0, 200, 56)
    tf.set_last_rect(0, 0, 200, 56)

    trailing = tf.trailing_icon
    assert isinstance(trailing, IconButton)
    rect = trailing.layout_rect
    assert rect is not None
    ix, iy, iw, ih = rect
    cx, cy = ix + iw / 2, iy + ih / 2
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, cx, cy, button=1)
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, cx, cy, button=1)

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


def test_text_field_input_filter_is_applied_to_typing() -> None:
    tf = TextField(value="", input_filter=digits_only())

    for ch in "1a2":
        tf._editable._handle_text(ch)

    assert tf.value == "12"


def test_text_field_input_filter_composes() -> None:
    tf = TextField(value="", input_filter=digits_only() | max_length(3))

    for ch in "1a2b3c4":
        tf._editable._handle_text(ch)

    assert tf.value == "123"


def test_text_field_input_filter_does_not_touch_an_assigned_value() -> None:
    """A filter governs what is typeable, not what the owner may store."""
    tf = TextField(value="preset", input_filter=digits_only())
    assert tf.value == "preset"

    tf.value = "still not digits"

    assert tf.value == "still not digits"
