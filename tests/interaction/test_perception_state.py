"""Tests for the interactive state ``describe_tree`` reports per node.

This is the half of a widget's state ``describe_state`` structurally cannot
reach: ``disabled`` and ``focused`` are plain fields of an ``InteractionState``,
never observables, and ``value`` is bound under whatever private attribute the
widget chose. So these run against real widgets rather than fakes -- what is
under test is whether the live plumbing publishes the flag at all, which a fake
node would answer by construction.

The narrower rules -- which source wins, what is omitted -- are in
``tests/dev/test_perception.py``.
"""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet._interaction.perception import describe_tree
from nuiitivet.layout.column import Column
from nuiitivet.material.slider import HorizontalRangeSlider
from nuiitivet.observable import Observable
from nuiitivet.testing import mount
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.text_field import TextFieldBase
from nuiitivet.widgets.toggleable import Toggleable


def _state_of(root: Any, type_name: str, index: int = 0) -> Optional[dict[str, Any]]:
    """Return the reported ``state`` of the ``index``-th ``type_name`` node."""
    found: list[dict[str, Any]] = []

    def walk(node: dict[str, Any]) -> None:
        if node["type"] == type_name:
            found.append(node)
        for child in node.get("children", ()):
            walk(child)

    walk(describe_tree(root))
    return found[index].get("state")


def test_disabled_widget_reports_disabled() -> None:
    off, on = Clickable(disabled=True), Clickable()
    with mount(Column(children=[off, on])) as host:
        host.layout(300, 200)

        assert _state_of(host.root, "Clickable", 0) == {"disabled": True}
        assert _state_of(host.root, "Clickable", 1) is None


def test_toggleable_reports_its_checked_state_as_value() -> None:
    with mount(Toggleable(value=True)) as host:
        host.layout(300, 200)

        assert _state_of(host.root, "Toggleable") == {"value": True}


def test_tristate_toggleable_reports_the_indeterminate_value() -> None:
    """``None`` is the third state, not "no value" -- it has to survive the dump."""
    with mount(Toggleable(value=None, tristate=True)) as host:
        host.layout(300, 200)

        assert _state_of(host.root, "Toggleable") == {"value": None}


def test_text_field_reports_its_current_text() -> None:
    field = TextFieldBase(value="hello")
    with mount(field) as host:
        host.layout(300, 200)

        assert _state_of(host.root, "TextFieldBase") == {"value": "hello"}

        field.value = "world"
        host.settle()
        assert _state_of(host.root, "TextFieldBase") == {"value": "world"}


def test_range_slider_reports_its_pair_however_it_was_bound() -> None:
    """A composite value rides the same ``value`` name as every scalar one.

    Bound as plain floats the two ends are not observables at all, so
    ``describe_state`` reports nothing for the widget; bound as observables it
    reports them under the private attributes they landed in. Either way this is
    the dump that names the value.
    """
    bound = HorizontalRangeSlider(value_start=Observable(0.2), value_end=Observable(0.8))
    plain = HorizontalRangeSlider(value_start=0.3, value_end=0.7)
    with mount(Column(children=[bound, plain])) as host:
        host.layout(600, 300)

        assert _state_of(host.root, "HorizontalRangeSlider", 0) == {"value": [0.2, 0.8]}
        assert _state_of(host.root, "HorizontalRangeSlider", 1) == {"value": [0.3, 0.7]}


def test_a_plain_container_reports_no_state() -> None:
    with mount(Column(children=[Clickable()])) as host:
        host.layout(300, 200)

        assert _state_of(host.root, "Column") is None


def test_tab_moves_the_reported_focus(nuiitivet_app) -> None:
    first, second = Clickable(), Clickable()
    app = nuiitivet_app(Column(children=[first, second]), size=(300, 200))

    app.key("tab")
    assert _state_of(app.window.root, "Clickable", 0) == {"focused": True}
    assert _state_of(app.window.root, "Clickable", 1) is None

    app.key("tab")
    assert _state_of(app.window.root, "Clickable", 0) is None
    assert _state_of(app.window.root, "Clickable", 1) == {"focused": True}
