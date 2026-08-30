from unittest.mock import MagicMock, patch

import pytest

from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.icon import Icon
from nuiitivet.material.buttons import IconButton
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.text_editing import TextRange
from nuiitivet.observable import Observable
from nuiitivet.input.codes import (
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_LEFT,
)
from nuiitivet.input.pointer import PointerEventType

from tests.helpers.pointer import send_pointer_event_for_test_via_app_routing


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
                    # A bare (windowless) tree writes no IME cursor rect; the
                    # cursor itself still paints.
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

    # The bound observable is the field's value cell: edits are written back
    # to it directly, with no callback to wire up (#575).
    tf = TextField(value=state)

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
    # The caret was at 6 ("Start!") and is clamped into the shorter text.
    assert tf._editable._state_internal.value.selection == TextRange(5, 5)

    tf.on_unmount()


def test_text_field_observable_value_is_two_way() -> None:
    """A writable observable is the field's value cell, so edits land in it."""
    state = _make_obs("Start")
    tf = TextField(value=state)

    tf.mount(MagicMock())
    assert tf.value == "Start"

    tf._editable._handle_text("!")
    assert tf.value == "Start!"
    assert state.value == "Start!"

    tf.on_unmount()


def test_text_field_read_only_observable_value_is_display_only() -> None:
    """A read-only source has nowhere to write, so it is not written to."""
    source = _make_obs("Start")
    derived = source.map(lambda s: s.upper())
    tf = TextField(value=derived)

    tf.mount(MagicMock())
    assert tf.value == "START"

    tf._editable._handle_text("!")
    assert tf.value == "START!"
    assert source.value == "Start"

    tf.on_unmount()


def test_text_field_bind_updates_observable() -> None:
    state = _make_obs("Start")
    tf = TextField(state)

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


def test_text_field_decorative_icons_are_plain_icons() -> None:
    tf = TextField(value="", leading_icon="search", trailing_icon="close")
    assert isinstance(tf.leading_icon, Icon)
    assert isinstance(tf.trailing_icon, Icon)


def test_text_field_tappable_icons_are_icon_buttons() -> None:
    """A tap callback upgrades the icon to a standard IconButton (state layers)."""
    tf = TextField(
        value="",
        leading_icon="search",
        on_tap_leading_icon=lambda: None,
        trailing_icon="close",
        on_tap_trailing_icon=lambda: None,
    )
    assert isinstance(tf.leading_icon, IconButton)
    assert isinstance(tf.trailing_icon, IconButton)


def test_text_field_rejects_widget_icon_instances() -> None:
    with pytest.raises(TypeError):
        TextField(value="", leading_icon=Icon("search"))  # type: ignore[arg-type]


def _click_at(root, x: float, y: float) -> None:
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, x, y, button=1)
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, x, y, button=1)


def _icon_button(icon) -> IconButton:
    """Assert ``icon`` is an IconButton and return it (narrows Optional[Widget])."""
    assert isinstance(icon, IconButton)
    return icon


def _icon_center(icon, ox: float = 0.0, oy: float = 0.0) -> tuple[float, float]:
    """Return the root-space center of a tappable icon offset by ``(ox, oy)``."""
    rect = _icon_button(icon).layout_rect
    assert rect is not None
    ix, iy, iw, ih = rect
    return ox + ix + iw / 2, oy + iy + ih / 2


def _mount_field_at(tf: TextField, ox: int, oy: int, w: int = 200, h: int = 56):
    """Place ``tf`` inside a root Box at ``(ox, oy)`` and return the root."""
    root = Box()
    root.add_child(tf)
    root.layout(ox + w + 50, oy + h + 50)
    root.set_layout_rect(0, 0, ox + w + 50, oy + h + 50)
    root.set_last_rect(0, 0, ox + w + 50, oy + h + 50)
    tf.layout(w, h)
    tf.set_layout_rect(ox, oy, w, h)
    tf.set_last_rect(ox, oy, w, h)
    return root


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
    root = _mount_field_at(tf, 0, 0)

    for icon in (tf.leading_icon, tf.trailing_icon):
        cx, cy = _icon_center(icon)
        _click_at(root, cx, cy)

    assert leading_tapped is True
    assert trailing_tapped is True


def test_text_field_invokes_icon_tap_callbacks_when_field_is_offset_from_root() -> None:
    """Hit testing must keep working when the field is offset from the root.

    Regression guard for #300: pointer events arrive in root coordinates, and
    the tappable icon (an IconButton child) is discovered through the
    framework's coordinate-translating hit test rather than a field-local
    rectangle comparison.
    """
    trailing_tapped = False

    def _on_trailing() -> None:
        nonlocal trailing_tapped
        trailing_tapped = True

    tf = TextField(value="", trailing_icon="close", on_tap_trailing_icon=_on_trailing)
    root = _mount_field_at(tf, 24, 24)

    cx, cy = _icon_center(tf.trailing_icon, 24, 24)
    _click_at(root, cx, cy)

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
    root = _mount_field_at(tf, 0, 0)

    _click_at(root, 100, 28)

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
    root = _mount_field_at(tf, 0, 0)

    cx, cy = _icon_center(tf.leading_icon)
    _click_at(root, cx, cy)

    assert leading_tapped is False


def test_text_field_tappable_icon_shows_hover_and_press_feedback() -> None:
    """The tappable icon renders interaction feedback (state layers) — #302."""
    tf = TextField(value="", trailing_icon="close", on_tap_trailing_icon=lambda: None)
    root = _mount_field_at(tf, 24, 24)

    icon = _icon_button(tf.trailing_icon)
    cx, cy = _icon_center(icon, 24, 24)

    assert icon.state.hovered is False
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.ENTER, cx, cy)
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.HOVER, cx, cy)
    assert icon.state.hovered is True

    send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, cx, cy, button=1)
    assert icon.state.pressed is True
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, cx, cy, button=1)
    assert icon.state.pressed is False


def test_text_field_disabling_field_disables_tappable_icon() -> None:
    tapped = False

    def _on_trailing() -> None:
        nonlocal tapped
        tapped = True

    tf = TextField(value="", trailing_icon="close", on_tap_trailing_icon=_on_trailing)
    root = _mount_field_at(tf, 0, 0)
    tf.disabled = True

    icon = _icon_button(tf.trailing_icon)
    assert icon.disabled is True
    cx, cy = _icon_center(icon)
    _click_at(root, cx, cy)
    assert tapped is False


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


def test_text_field_supporting_text_does_not_imply_the_error_state() -> None:
    """The message and the visual state are separate axes, each with its own source."""
    supporting_text = _make_obs(None)
    style = TextFieldStyle.outlined()
    tf = TextField(value="", supporting_text=supporting_text, style=style)

    tf.mount(MagicMock())
    assert tf.supporting_text is None
    assert tf.is_error is False

    supporting_text.value = "Between 1 and 10"
    assert tf.supporting_text == "Between 1 and 10"
    # A message is a message; only is_error recolors the field.
    assert tf.is_error is False
    assert tf._editable.cursor_color == style.cursor_color

    tf.on_unmount()


def test_text_field_error_state_needs_no_message() -> None:
    """is_error stands alone: the field is flagged with nothing written below it."""
    style = TextFieldStyle.outlined()
    tf = TextField(value="", is_error=True, style=style)

    tf.mount(MagicMock())
    assert tf.supporting_text is None
    assert tf.is_error is True
    assert tf._editable.cursor_color == style.error_cursor_color

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
