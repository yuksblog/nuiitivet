from typing import Any, cast

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.layout.column import Column
from nuiitivet.material.selection_controls import RadioButton, RadioGroup
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box
from tests.helpers.pointer import send_pointer_event_for_test


def _click(widget) -> None:
    assert send_pointer_event_for_test(widget, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(widget, PointerEventType.RELEASE) is True


def test_radio_button_does_not_accept_group_value_or_on_change() -> None:
    radio_ctor = cast(Any, RadioButton)

    try:
        radio_ctor("a", on_change=lambda _v: None)
        assert False, "RadioButton should not accept on_change"
    except TypeError:
        pass

    try:
        radio_ctor("a", group_value="a")
        assert False, "RadioButton should not accept group_value"
    except TypeError:
        pass


def test_radio_group_updates_on_nested_descendant_click() -> None:
    selected = Observable("a")
    called: list[object | None] = []

    radio_a = RadioButton("a")
    radio_b = RadioButton("b")

    nested = Box(
        child=Column(
            children=[
                Box(child=radio_a),
                Box(child=Box(child=radio_b)),
            ]
        )
    )

    group = RadioGroup(nested, value=selected, on_change=lambda v: called.append(v))

    _click(radio_b)

    assert selected.value == "b"
    assert called == ["b"]
    assert group is not None


def test_radio_group_nearest_ancestor_wins() -> None:
    outer_selected = Observable("outer-a")
    inner_selected = Observable("inner-a")

    outer_radio = RadioButton("outer-a")
    inner_radio_a = RadioButton("inner-a")
    inner_radio_b = RadioButton("inner-b")

    inner_group = RadioGroup(
        Column(children=[Box(child=inner_radio_a), Box(child=inner_radio_b)]),
        value=inner_selected,
    )

    outer_group = RadioGroup(
        Column(children=[Box(child=outer_radio), Box(child=inner_group)]),
        value=outer_selected,
    )

    _click(inner_radio_b)

    assert inner_selected.value == "inner-b"
    assert outer_selected.value == "outer-a"

    _click(outer_radio)
    assert outer_selected.value == "outer-a"

    # Keep references alive to avoid lints about unused widgets in this construction-only test.
    assert outer_group is not None
