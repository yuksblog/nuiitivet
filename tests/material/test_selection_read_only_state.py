"""A read-only State given to a selection control is shown, never written."""

from typing import Optional

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.material.selection_controls import Checkbox, RadioButton, RadioGroup, Switch
from nuiitivet.observable import State
from nuiitivet.testing import AppHarness
from nuiitivet.widgets.toggleable import Toggleable

SIZE = (300, 300)


def test_switch_with_read_only_state_calls_on_change_and_writes_nothing() -> None:
    source = State(False)
    calls: list[bool] = []
    switch = Switch(source.map(lambda v: v), on_change=calls.append, key="sw")

    with AppHarness(switch, size=SIZE) as app:
        app.click(key="sw")
        app.settle()

        assert calls == [True]
        assert source.value is False
        assert switch.value is False


def test_switch_with_read_only_state_follows_the_source() -> None:
    source = State(False)
    calls: list[bool] = []

    def on_change(on: bool) -> None:
        calls.append(on)
        source.value = on

    switch = Switch(source.map(lambda v: v), on_change=on_change, key="sw")

    with AppHarness(switch, size=SIZE) as app:
        app.click(key="sw")
        app.settle()
        assert switch.value is True
        assert switch.state.checked is True

        app.click(key="sw")
        app.settle()
        assert calls == [True, False]
        assert switch.value is False


def test_checkbox_with_read_only_state_shows_the_state_not_the_click() -> None:
    source: State[Optional[bool]] = State(False)
    calls: list[Optional[bool]] = []
    checkbox = Checkbox(source.map(lambda v: v), on_toggle=calls.append, key="cb")

    with AppHarness(checkbox, size=SIZE) as app:
        app.click(key="cb")
        app.settle()

        assert calls == [True]
        assert source.value is False
        assert checkbox.value is False

        source.value = True
        app.settle()
        assert checkbox.value is True


def test_checkbox_with_read_only_indeterminate_writes_only_checked() -> None:
    checked = State(False)
    indeterminate_source = State(True)
    calls: list[Optional[bool]] = []
    checkbox = Checkbox(
        checked,
        indeterminate=indeterminate_source.map(lambda v: v),
        on_toggle=calls.append,
        key="cb",
    )

    with AppHarness(checkbox, size=SIZE) as app:
        app.click(key="cb")
        app.settle()

        assert calls == [True]
        assert checked.value is True
        assert indeterminate_source.value is True
        assert checkbox.value is None


def test_radio_group_with_read_only_state_calls_on_change_and_writes_nothing() -> None:
    source = State("a")
    calls: list[object | None] = []
    radio_b = RadioButton("b", key="b")
    group = RadioGroup(
        Column([RadioButton("a", key="a"), radio_b]),
        value=source.map(lambda v: v),
        on_change=calls.append,
    )

    with AppHarness(group, size=SIZE) as app:
        app.click(key="b")
        app.settle()

        assert calls == ["b"]
        assert source.value == "a"
        assert group.value == "a"
        assert radio_b.value is False

        source.value = "b"
        app.settle()
        assert group.value == "b"
        assert radio_b.value is True


def test_assigning_value_through_a_read_only_state_raises() -> None:
    source = State(False)
    toggle = Toggleable(source.map(lambda v: v))
    group = RadioGroup(Column([]), value=source.map(lambda v: "a" if v else "b"))

    with pytest.raises(TypeError):
        toggle.value = True
    with pytest.raises(TypeError):
        group.value = "a"
