from __future__ import annotations

import pytest

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.buttons import ToggleButton
from nuiitivet.material.styles.toggle_button_style import ToggleButtonStyle
from nuiitivet.observable import Observable
from tests.helpers.pointer import send_pointer_event_for_test


def _make_obs(initial: bool):
    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


_STYLE_FACTORIES = [
    ToggleButtonStyle.filled,
    ToggleButtonStyle.outlined,
    ToggleButtonStyle.elevated,
    ToggleButtonStyle.tonal,
]


def _make_toggle(style_factory, **kwargs) -> ToggleButton:
    return ToggleButton("Toggle", style=style_factory(), **kwargs)


@pytest.mark.parametrize("style_factory", _STYLE_FACTORIES)
def test_toggle_button_accepts_selected_bool(style_factory):
    btn_unselected = _make_toggle(style_factory, selected=False)
    btn_selected = _make_toggle(style_factory, selected=True)

    assert btn_unselected.selected is False
    assert btn_selected.selected is True


@pytest.mark.parametrize("style_factory", _STYLE_FACTORIES)
def test_toggle_button_click_toggles_and_calls_on_change(style_factory):
    called: list[bool] = []

    btn = _make_toggle(style_factory, selected=False, on_change=lambda v: called.append(v))

    assert send_pointer_event_for_test(btn, PointerEventType.PRESS) is True
    assert btn.selected is False
    assert called == []

    assert send_pointer_event_for_test(btn, PointerEventType.RELEASE) is True
    assert btn.selected is True
    assert called == [True]


@pytest.mark.parametrize("style_factory", _STYLE_FACTORIES)
def test_toggle_button_accepts_observable_selected(style_factory):
    selected = _make_obs(False)
    called: list[bool] = []

    btn = _make_toggle(style_factory, selected=selected, on_change=lambda v: called.append(v))
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


@pytest.mark.parametrize("style_factory", _STYLE_FACTORIES)
def test_toggle_button_selected_unselected_styles_differ(style_factory):
    btn = _make_toggle(style_factory, selected=False)
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


@pytest.mark.parametrize("style_factory", _STYLE_FACTORIES)
def test_toggle_button_disabled_does_not_toggle(style_factory):
    called: list[bool] = []
    btn = _make_toggle(style_factory, selected=False, disabled=True, on_change=lambda v: called.append(v))

    assert send_pointer_event_for_test(btn, PointerEventType.PRESS) is False
    assert send_pointer_event_for_test(btn, PointerEventType.RELEASE) is False

    assert btn.selected is False
    assert called == []
