from __future__ import annotations

import pytest

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.buttons import IconButton, IconToggleButton
from nuiitivet.material.icon import Icon
from nuiitivet.material.styles.button_style import IconButtonStyle, IconToggleButtonStyle
from nuiitivet.observable.value import _ObservableValue
from tests.helpers.pointer import send_pointer_event_for_test


@pytest.mark.parametrize(
    "style",
    [
        IconButtonStyle.standard(),
        IconButtonStyle.filled(),
        IconButtonStyle.outlined(),
        IconButtonStyle.tonal(),
        IconButtonStyle.vibrant(),
        IconButtonStyle.filled_vibrant(),
        IconButtonStyle.outlined_vibrant(),
        IconButtonStyle.tonal_vibrant(),
    ],
)
def test_icon_button_renders_icon_only_and_circular(style):
    btn = IconButton("add", style=style)

    assert len(btn.children) == 1
    child = btn.children[0]
    assert isinstance(child, Icon)
    assert child.name == "add"
    assert btn.style.corner_radius == 20


@pytest.mark.parametrize(
    "style",
    [
        IconButtonStyle.standard(),
        IconButtonStyle.filled(),
        IconButtonStyle.outlined(),
        IconButtonStyle.tonal(),
        IconButtonStyle.vibrant(),
        IconButtonStyle.filled_vibrant(),
        IconButtonStyle.outlined_vibrant(),
        IconButtonStyle.tonal_vibrant(),
    ],
)
def test_icon_button_disabled_blocks_pointer_interaction(style):
    btn = IconButton("add", style=style, disabled=True)

    assert send_pointer_event_for_test(btn, PointerEventType.PRESS) is False
    assert send_pointer_event_for_test(btn, PointerEventType.RELEASE) is False


@pytest.mark.parametrize(
    "style",
    [
        IconToggleButtonStyle.standard(),
        IconToggleButtonStyle.filled(),
        IconToggleButtonStyle.outlined(),
        IconToggleButtonStyle.tonal(),
    ],
)
def test_icon_toggle_button_toggles_and_calls_on_change(style):
    called: list[bool] = []
    btn = IconToggleButton("favorite", selected=False, on_change=lambda v: called.append(v), style=style)

    assert send_pointer_event_for_test(btn, PointerEventType.PRESS) is True
    assert btn.selected is False
    assert send_pointer_event_for_test(btn, PointerEventType.RELEASE) is True

    assert btn.selected is True
    assert called == [True]


@pytest.mark.parametrize(
    "style",
    [
        IconToggleButtonStyle.standard(),
        IconToggleButtonStyle.filled(),
        IconToggleButtonStyle.outlined(),
        IconToggleButtonStyle.tonal(),
    ],
)
def test_icon_toggle_button_selected_unselected_appearances_differ(style):
    btn = IconToggleButton("favorite", selected=False, style=style)
    unselected_signature = (
        btn.style.background,
        btn.style.foreground,
        btn.style.border_color,
        btn.style.border_width,
    )

    btn.selected = True
    selected_signature = (
        btn.style.background,
        btn.style.foreground,
        btn.style.border_color,
        btn.style.border_width,
    )

    assert unselected_signature != selected_signature


def test_icon_button_born_disabled_hides_focus_ring_on_pointer_focus(nuiitivet_app) -> None:
    disabled = _ObservableValue(True)
    btn = IconButton("add", disabled=disabled, on_click=lambda: None, key="btn")
    app = nuiitivet_app(btn, size=(200, 200))

    disabled.value = False
    app.click(key="btn")

    assert btn.state.focused is True
    assert btn.should_show_focus_ring is False


def test_icon_button_born_disabled_activates_on_space_and_enter(nuiitivet_app) -> None:
    clicked: list[int] = []
    disabled = _ObservableValue(True)
    btn = IconButton("add", disabled=disabled, on_click=lambda: clicked.append(1), key="btn")
    app = nuiitivet_app(btn, size=(200, 200))

    disabled.value = False
    app.click(key="btn")
    app.key("space")
    app.key("enter")

    assert clicked == [1, 1, 1]
