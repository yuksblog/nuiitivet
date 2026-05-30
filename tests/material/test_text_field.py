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
from nuiitivet.input.pointer import PointerEvent, PointerEventType


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


def test_text_field_obscure_text_sets_editable_masking() -> None:
    tf = TextField(value="secret", obscure_text=True)
    assert tf._editable.obscure_text is True


def test_text_field_obscure_text_masks_rendered_text() -> None:
    tf = TextField(value="secret", obscure_text=True)

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
                with patch("nuiitivet.widgets.editable_text.make_text_blob", return_value=MagicMock()) as blob_mock:
                    tf._editable.paint(canvas, 0, 0, 200, 56)

    blob_mock.assert_called_with("••••••", mock_font)


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


def test_text_field_invokes_icon_tap_callbacks_on_press() -> None:
    leading_tapped = False
    trailing_tapped = False

    def _on_leading() -> None:
        nonlocal leading_tapped
        leading_tapped = True

    def _on_trailing() -> None:
        nonlocal trailing_tapped
        trailing_tapped = True

    tf = TextField(
        value="",
        leading_icon="search",
        on_tap_leading_icon=_on_leading,
        trailing_icon="close",
        on_tap_trailing_icon=_on_trailing,
    )
    tf.layout(200, 56)

    tf._handle_press(PointerEvent.mouse_event(1, PointerEventType.PRESS, 13, 28))
    tf._handle_press(PointerEvent.mouse_event(2, PointerEventType.PRESS, 187, 28))

    assert leading_tapped is True
    assert trailing_tapped is True


def test_text_field_does_not_invoke_icon_callbacks_when_pressing_non_icon_area() -> None:
    leading_tapped = False
    trailing_tapped = False

    def _on_leading() -> None:
        nonlocal leading_tapped
        leading_tapped = True

    def _on_trailing() -> None:
        nonlocal trailing_tapped
        trailing_tapped = True

    tf = TextField(
        value="",
        leading_icon="search",
        on_tap_leading_icon=_on_leading,
        trailing_icon="close",
        on_tap_trailing_icon=_on_trailing,
    )
    tf.layout(200, 56)

    tf._handle_press(PointerEvent.mouse_event(1, PointerEventType.PRESS, 100, 28))

    assert leading_tapped is False
    assert trailing_tapped is False


def test_text_field_does_not_invoke_icon_callbacks_when_disabled() -> None:
    leading_tapped = False

    def _on_leading() -> None:
        nonlocal leading_tapped
        leading_tapped = True

    tf = TextField(
        value="",
        leading_icon="search",
        on_tap_leading_icon=_on_leading,
        disabled=True,
    )
    tf.layout(200, 56)

    tf._handle_press(PointerEvent.mouse_event(1, PointerEventType.PRESS, 13, 28))

    assert leading_tapped is False


def test_text_field_supporting_text_uses_dedicated_color_tokens() -> None:
    style = TextFieldStyle.outlined().copy_with(
        supporting_text_color="#112233",
        error_supporting_text_color="#aa0000",
    )
    tf = TextField(value="", supporting_text="hint", is_error=False, style=style)

    mock_font = MagicMock()
    metrics = MagicMock()
    metrics.fAscent = -10
    metrics.fDescent = 3
    mock_font.getMetrics = MagicMock(return_value=metrics)
    mock_font.setSize = MagicMock()

    recorded_specs: list[object] = []

    def _resolve(spec, **kwargs):
        recorded_specs.append(spec)
        return (0, 0, 0, 255)

    canvas = MagicMock()

    with patch.object(tf, "_get_font", return_value=mock_font):
        with patch("nuiitivet.material.text_fields.resolve_color_to_rgba", side_effect=_resolve):
            with patch("nuiitivet.material.text_fields.make_paint", return_value=MagicMock()):
                with patch("nuiitivet.material.text_fields.make_text_blob", return_value=MagicMock()):
                    tf._draw_supporting_text(canvas, 0, 0, 56)

    assert style.supporting_text_color in recorded_specs

    tf.is_error = True
    recorded_specs.clear()

    with patch.object(tf, "_get_font", return_value=mock_font):
        with patch("nuiitivet.material.text_fields.resolve_color_to_rgba", side_effect=_resolve):
            with patch("nuiitivet.material.text_fields.make_paint", return_value=MagicMock()):
                with patch("nuiitivet.material.text_fields.make_text_blob", return_value=MagicMock()):
                    tf._draw_supporting_text(canvas, 0, 0, 56)

    assert style.error_supporting_text_color in recorded_specs


def test_text_field_label_supports_observable() -> None:
    label = _make_obs("Name")
    tf = TextField(value="", label=label)

    tf.mount(MagicMock())
    assert tf.label == "Name"

    label.value = "Email"
    assert tf.label == "Email"

    tf.on_unmount()


def test_text_field_supporting_text_and_is_error_support_observable() -> None:
    supporting_text = _make_obs(None)
    is_error = _make_obs(False)
    style = TextFieldStyle.outlined()
    tf = TextField(value="", supporting_text=supporting_text, is_error=is_error, style=style)

    with patch.object(tf, "mark_needs_layout", wraps=tf.mark_needs_layout) as mark_needs_layout:
        tf.mount(MagicMock())
        assert tf.supporting_text is None
        assert tf._editable.cursor_color == style.cursor_color

        supporting_text.value = "Need at least 8 characters"
        assert tf.supporting_text == "Need at least 8 characters"
        assert tf._editable.cursor_color == style.cursor_color

        is_error.value = True
        assert tf._editable.cursor_color == style.error_cursor_color
        assert mark_needs_layout.called is True

    tf.on_unmount()


def test_text_field_error_text_legacy_alias_still_updates_error_state() -> None:
    error_text = _make_obs(None)
    style = TextFieldStyle.outlined()
    tf = TextField(value="", error_text=error_text, style=style)

    tf.mount(MagicMock())
    assert tf.error_text is None
    assert tf.supporting_text is None
    assert tf.is_error is False
    assert tf._editable.cursor_color == style.cursor_color

    error_text.value = "Oops"
    assert tf.error_text == "Oops"
    assert tf.supporting_text == "Oops"
    assert tf.is_error is True
    assert tf._editable.cursor_color == style.error_cursor_color

    error_text.value = None
    assert tf.error_text is None
    assert tf.is_error is False
    assert tf._editable.cursor_color == style.cursor_color

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
