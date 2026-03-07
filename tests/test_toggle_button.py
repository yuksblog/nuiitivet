from __future__ import annotations

import pytest

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.buttons import (
    FilledToggleButton,
    OutlinedToggleButton,
    TextToggleButton,
    TonalToggleButton,
)
from nuiitivet.observable import Observable
from tests.helpers.pointer import send_pointer_event_for_test


def _make_obs(initial: bool):
    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


@pytest.mark.parametrize(
    "button_cls",
    [FilledToggleButton, OutlinedToggleButton, TextToggleButton, TonalToggleButton],
)
def test_toggle_button_accepts_selected_bool(button_cls):
    btn_unselected = button_cls("Toggle", selected=False)
    btn_selected = button_cls("Toggle", selected=True)

    assert btn_unselected.selected is False
    assert btn_selected.selected is True


@pytest.mark.parametrize(
    "button_cls",
    [FilledToggleButton, OutlinedToggleButton, TextToggleButton, TonalToggleButton],
)
def test_toggle_button_click_toggles_and_calls_on_change(button_cls):
    called: list[bool] = []

    btn = button_cls("Toggle", selected=False, on_change=lambda v: called.append(v))

    assert send_pointer_event_for_test(btn, PointerEventType.PRESS) is True
    assert btn.selected is False
    assert called == []

    assert send_pointer_event_for_test(btn, PointerEventType.RELEASE) is True
    assert btn.selected is True
    assert called == [True]


@pytest.mark.parametrize(
    "button_cls",
    [FilledToggleButton, OutlinedToggleButton, TextToggleButton, TonalToggleButton],
)
def test_toggle_button_accepts_observable_selected(button_cls):
    selected = _make_obs(False)
    called: list[bool] = []

    btn = button_cls("Toggle", selected=selected, on_change=lambda v: called.append(v))
    btn.on_mount()
    try:
        assert btn.selected is False

        selected.value = True
        assert btn.selected is True
        assert btn.state.checked is True

        assert send_pointer_event_for_test(btn, PointerEventType.PRESS) is True
        assert send_pointer_event_for_test(btn, PointerEventType.RELEASE) is True

        assert btn.selected is False
        assert selected.value is False
        assert called == [False]
    finally:
        btn.on_unmount()


@pytest.mark.parametrize(
    "button_cls",
    [FilledToggleButton, OutlinedToggleButton, TextToggleButton, TonalToggleButton],
)
def test_toggle_button_selected_unselected_styles_differ(button_cls):
    btn = button_cls("Toggle", selected=False)
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


@pytest.mark.parametrize(
    "button_cls",
    [FilledToggleButton, OutlinedToggleButton, TextToggleButton, TonalToggleButton],
)
def test_toggle_button_disabled_does_not_toggle(button_cls):
    called: list[bool] = []
    btn = button_cls("Toggle", selected=False, disabled=True, on_change=lambda v: called.append(v))

    assert send_pointer_event_for_test(btn, PointerEventType.PRESS) is False
    assert send_pointer_event_for_test(btn, PointerEventType.RELEASE) is False

    assert btn.selected is False
    assert called == []
