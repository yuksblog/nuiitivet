from __future__ import annotations

from typing import Any, cast

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.chip import AssistChip, FilterChip, InputChip, SuggestionChip
from nuiitivet.material.icon import Icon
from nuiitivet.material.text import Text
from nuiitivet.observable import Observable
from nuiitivet.widgets.interaction import FocusNode
from tests.helpers.pointer import send_pointer_event_for_test, send_pointer_event_for_test_via_app_routing


def _content_children(chip) -> list:
    content = chip.children_snapshot()[0]
    assert isinstance(content, Container)
    row = content.children_snapshot()[0]
    return row.children_snapshot()


def test_assist_chip_with_label_only() -> None:
    chip = AssistChip("Assist")
    children = _content_children(chip)

    assert len(children) == 1
    assert isinstance(children[0], Text)
    assert children[0].label == "Assist"


def test_assist_chip_with_leading_icon() -> None:
    chip = AssistChip("Assist", leading_icon="add")
    children = _content_children(chip)

    assert len(children) == 2
    assert isinstance(children[0], Icon)
    assert isinstance(children[1], Text)


def test_input_chip_requires_trailing_icon() -> None:
    with pytest.raises(TypeError):
        cast(Any, InputChip)("Input")


def test_input_chip_includes_trailing_icon() -> None:
    chip = InputChip("Input", trailing_icon="close")
    children = _content_children(chip)

    assert len(children) == 2
    assert isinstance(children[0], Text)
    assert isinstance(children[1], Icon)


def test_input_chip_trailing_icon_callback_on_press() -> None:
    tapped = False

    def _on_trailing() -> None:
        nonlocal tapped
        tapped = True

    chip = InputChip("Input", trailing_icon="close", on_trailing_icon_click=_on_trailing)
    chip.set_layout_rect(0, 0, 200, 48)
    chip.layout(200, 48)

    trailing_target = chip._trailing_icon_tap_target
    assert trailing_target is not None
    assert trailing_target.global_layout_rect is not None

    rx, ry, rw, rh = trailing_target.global_layout_rect
    assert send_pointer_event_for_test_via_app_routing(chip, PointerEventType.PRESS, rx + rw / 2, ry + rh / 2) is True
    assert send_pointer_event_for_test_via_app_routing(chip, PointerEventType.RELEASE, rx + rw / 2, ry + rh / 2) is True

    assert tapped is True


def test_input_chip_trailing_icon_callback_not_called_on_non_icon_press() -> None:
    tapped = False

    def _on_trailing() -> None:
        nonlocal tapped
        tapped = True

    chip = InputChip("Input", trailing_icon="close", on_trailing_icon_click=_on_trailing)
    chip.set_layout_rect(0, 0, 200, 48)
    chip.layout(200, 48)

    send_pointer_event_for_test_via_app_routing(chip, PointerEventType.PRESS, 20, 24)
    send_pointer_event_for_test_via_app_routing(chip, PointerEventType.RELEASE, 20, 24)

    assert tapped is False


def test_input_chip_trailing_icon_press_suppresses_main_click() -> None:
    trailing_tapped = False
    chip_clicked = False

    def _on_trailing() -> None:
        nonlocal trailing_tapped
        trailing_tapped = True

    def _on_click() -> None:
        nonlocal chip_clicked
        chip_clicked = True

    chip = InputChip(
        "Input",
        trailing_icon="close",
        on_trailing_icon_click=_on_trailing,
        on_click=_on_click,
    )
    chip.set_layout_rect(0, 0, 200, 48)
    chip.layout(200, 48)

    trailing_target = chip._trailing_icon_tap_target
    assert trailing_target is not None
    assert trailing_target.global_layout_rect is not None

    rx, ry, rw, rh = trailing_target.global_layout_rect
    assert send_pointer_event_for_test_via_app_routing(chip, PointerEventType.PRESS, rx + rw / 2, ry + rh / 2) is True
    assert send_pointer_event_for_test_via_app_routing(chip, PointerEventType.RELEASE, rx + rw / 2, ry + rh / 2) is True

    assert trailing_tapped is True
    assert chip_clicked is False


def test_input_chip_trailing_icon_target_is_focusable() -> None:
    chip = InputChip("Input", trailing_icon="close", on_trailing_icon_click=lambda: None)
    target = chip._trailing_icon_tap_target

    assert target is not None
    assert cast(Any, target).get_node(FocusNode) is not None


def test_suggestion_chip_basic() -> None:
    chip = SuggestionChip("Suggestion")
    children = _content_children(chip)

    assert len(children) == 1
    assert isinstance(children[0], Text)
    assert children[0].label == "Suggestion"


def test_filter_chip_click_toggles_selected() -> None:
    events: list[bool] = []
    chip = FilterChip("Filter", on_selected_change=lambda value: events.append(value))

    assert chip.selected is False
    assert send_pointer_event_for_test(chip, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(chip, PointerEventType.RELEASE) is True
    assert chip.selected is True
    assert events == [True]

    assert send_pointer_event_for_test(chip, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(chip, PointerEventType.RELEASE) is True
    assert chip.selected is False
    assert events == [True, False]


def test_filter_chip_observable_selected_sync() -> None:
    selected = Observable(False)
    chip = FilterChip("Filter", selected=selected)
    chip.on_mount()

    assert chip.selected is False
    selected.value = True
    assert chip.selected is True


def test_chip_horizontal_padding_without_icon_is_16() -> None:
    chip = AssistChip("Assist")
    content = chip.children_snapshot()[0]
    assert isinstance(content, Container)
    assert content.padding == (16, 0, 16, 0)


def test_chip_horizontal_padding_with_icon_is_8() -> None:
    chip = AssistChip("Assist", leading_icon="add")
    content = chip.children_snapshot()[0]
    assert isinstance(content, Container)
    assert content.padding == (8, 0, 8, 0)
