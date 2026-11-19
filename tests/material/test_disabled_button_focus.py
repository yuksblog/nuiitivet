"""A button keeps its own FocusNode while disabled, and the disabled state blocks focus.

A modifier that looks for the button's FocusNode, such as ``tooltip()``, must find
the button's own node whether the button was built enabled or disabled.
"""

from __future__ import annotations

from typing import Optional

from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import IconButton
from nuiitivet.material.text import Text
from nuiitivet.modifiers.tooltip import tooltip
from nuiitivet.observable import State
from nuiitivet.observable.value import _StateValue
from nuiitivet.widgets.interaction import FocusNode, FocusSource


def _build(enabled: _StateValue[bool], clicks: list[str]) -> Row:
    disabled = enabled.map(lambda e: not e)
    return Row(
        [
            IconButton("add", on_click=lambda: clicks.append("always"), key="always").modifier(
                tooltip(Text("tip"))
            ),
            IconButton("add", on_click=lambda: clicks.append("later"), disabled=disabled, key="later").modifier(
                tooltip(Text("tip"))
            ),
            IconButton(
                "add", on_click=lambda: clicks.append("later-no-tooltip"), disabled=disabled, key="later-no-tooltip"
            ),
        ],
        padding=40,
        gap=16,
    )


def _focused_owner(app) -> Optional[object]:
    node = app.window._focused_node
    return None if node is None else node.owner


def test_pointer_click_shows_no_focus_ring_once_enabled(nuiitivet_app) -> None:
    enabled = State(False)
    app = nuiitivet_app(_build(enabled, []), size=(400, 200))
    enabled.value = True
    app.settle()

    for key in ("always", "later", "later-no-tooltip"):
        app.click(key=key)
        button = app.get(key=key).widget
        assert button.state.focused, key
        assert not button.should_show_focus_ring, key


def test_space_and_enter_click_a_button_built_disabled_with_a_tooltip(nuiitivet_app) -> None:
    enabled = State(False)
    clicks: list[str] = []
    app = nuiitivet_app(_build(enabled, clicks), size=(400, 200))
    enabled.value = True
    app.settle()
    later = app.get(key="later").widget

    app.key("tab")
    app.key("tab")
    assert _focused_owner(app) is later
    assert later.should_show_focus_ring

    app.key("space")
    app.key("enter")
    assert clicks == ["later", "later"]


def test_button_built_disabled_is_one_focus_stop_with_its_own_node(nuiitivet_app) -> None:
    enabled = State(False)
    app = nuiitivet_app(_build(enabled, []), size=(400, 200))
    enabled.value = True
    app.settle()
    buttons = [app.get(key=key).widget for key in ("always", "later", "later-no-tooltip")]

    assert [node.owner for node in app.window._collect_focus_nodes()] == buttons
    for button in buttons:
        nodes = [node for node in button._nodes if isinstance(node, FocusNode)]
        assert len(nodes) == 1
        assert nodes[0]._on_key is not None


def test_disabled_button_takes_no_focus(nuiitivet_app) -> None:
    enabled = State(False)
    app = nuiitivet_app(_build(enabled, []), size=(400, 200))
    later = app.get(key="later").widget
    node = later.get_node(FocusNode)
    assert isinstance(node, FocusNode)

    assert [n.owner for n in app.window._collect_focus_nodes()] == [app.get(key="always").widget]

    app.click(key="later")
    assert _focused_owner(app) is not later

    node.request_focus(FocusSource.KEYBOARD)
    assert _focused_owner(app) is not later
    assert not later.state.focused
