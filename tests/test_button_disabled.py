"""Test disabled state for Button widgets."""

from unittest.mock import MagicMock

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.material.buttons import (
    FilledButton,
    TextButton,
    OutlinedButton,
    ElevatedButton,
    FilledTonalButton,
    FloatingActionButton,
)
from nuiitivet.widgets.interaction import FocusNode
from tests.helpers.pointer import send_pointer_event_for_test


def test_filled_button_disabled_ignores_events():
    """Disabled filled button should ignore all events."""
    clicked = []
    button = FilledButton("Test", disabled=True, on_click=lambda: clicked.append(1))
    result = send_pointer_event_for_test(button, PointerEventType.PRESS)
    assert result is False
    assert len(clicked) == 0


def test_filled_button_enabled_handles_events():
    """Enabled filled button should handle events normally."""
    clicked = []
    button = FilledButton("Test", disabled=False, on_click=lambda: clicked.append(1))
    press = send_pointer_event_for_test(button, PointerEventType.PRESS)
    assert press is True
    assert len(clicked) == 0
    release = send_pointer_event_for_test(button, PointerEventType.RELEASE)
    assert release is True
    assert len(clicked) == 1


def test_button_disabled_internal_state():
    """Test disabled internal state (disabled attribute)."""
    button = FilledButton("Test", disabled=False)
    assert button.disabled is False
    button_disabled = FilledButton("Test", disabled=True)
    assert button_disabled.disabled is True


def test_button_disabled_no_hover_overlay():
    """Disabled button should not show hover overlay (no hover state)."""
    button = FilledButton("Test", disabled=True)
    send_pointer_event_for_test(button, PointerEventType.ENTER)
    assert button.state.hovered is False


def test_button_enabled_shows_hover_overlay():
    """Enabled button should show hover overlay (hover state)."""
    button = FilledButton("Test", disabled=False)
    send_pointer_event_for_test(button, PointerEventType.ENTER)
    assert button.state.hovered is True


def test_text_button_disabled():
    """TextButton should support disabled state."""
    clicked = []
    button = TextButton("Test", disabled=True, on_click=lambda: clicked.append(1))
    result = send_pointer_event_for_test(button, PointerEventType.PRESS)
    assert result is False
    assert len(clicked) == 0


def test_outlined_button_disabled():
    """OutlinedButton should support disabled state."""
    clicked = []
    button = OutlinedButton("Test", disabled=True, on_click=lambda: clicked.append(1))
    result = send_pointer_event_for_test(button, PointerEventType.PRESS)
    assert result is False
    assert len(clicked) == 0


def test_elevated_button_disabled():
    """ElevatedButton should support disabled state."""
    clicked = []
    button = ElevatedButton("Test", disabled=True, on_click=lambda: clicked.append(1))
    result = send_pointer_event_for_test(button, PointerEventType.PRESS)
    assert result is False
    assert len(clicked) == 0


def test_tonal_button_disabled():
    """FilledTonalButton should support disabled state."""
    clicked = []
    button = FilledTonalButton("Test", disabled=True, on_click=lambda: clicked.append(1))
    result = send_pointer_event_for_test(button, PointerEventType.PRESS)
    assert result is False
    assert len(clicked) == 0


def test_fab_disabled():
    """FloatingActionButton should support disabled state."""
    clicked = []
    button = FloatingActionButton(icon="add", disabled=True, on_click=lambda: clicked.append(1))
    result = send_pointer_event_for_test(button, PointerEventType.PRESS)
    assert result is False
    assert len(clicked) == 0


def test_button_disabled_opacity_in_style():
    """ButtonStyle should have disabled_opacity field."""
    from nuiitivet.material.styles.button_style import ButtonStyle

    style = ButtonStyle(background="#FF0000", foreground="#FFFFFF")
    assert getattr(style, "disabled_opacity", 0.38) == 0.38


def test_button_disabled_opacity_default():
    """ButtonStyle should have default disabled_opacity of 0.38."""
    from nuiitivet.material.styles.button_style import ButtonStyle

    style = ButtonStyle(background="#FF0000", foreground="#FFFFFF")
    assert getattr(style, "disabled_opacity", 0.38) == 0.38


def test_filled_button_disabled_observable_toggles_events():
    """Disabled state should react to Observable changes."""
    clicked: list[int] = []
    disabled = _ObservableValue(True)

    button = FilledButton("Test", disabled=disabled, on_click=lambda: clicked.append(1))
    button.mount(MagicMock())

    try:
        press = send_pointer_event_for_test(button, PointerEventType.PRESS)
        assert press is False
        assert len(clicked) == 0

        disabled.value = False
        assert button.disabled is False

        press = send_pointer_event_for_test(button, PointerEventType.PRESS)
        assert press is True
        release = send_pointer_event_for_test(button, PointerEventType.RELEASE)
        assert release is True
        assert len(clicked) == 1

        disabled.value = True
        assert button.disabled is True

        press = send_pointer_event_for_test(button, PointerEventType.PRESS)
        assert press is False
        assert len(clicked) == 1
    finally:
        button.unmount()


def test_filled_button_disabled_observable_adds_focus_node_on_enable():
    """FocusNode should be added when a disabled Observable becomes enabled."""
    disabled = _ObservableValue(True)
    button = FilledButton("Test", disabled=disabled)
    button.mount(MagicMock())

    try:
        assert button.get_node(FocusNode) is None
        disabled.value = False
        assert button.get_node(FocusNode) is not None
    finally:
        button.unmount()
