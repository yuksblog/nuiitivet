"""Tests for Navigator intent resolution and back handling."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.material.transition_spec import MaterialTransitionSpec
from nuiitivet.navigation import Navigator
from nuiitivet.navigation.route import Route
from nuiitivet.transition.spec import EmptyTransitionSpec, Transitions
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.unmounted = False

    def on_unmount(self) -> None:
        self.unmounted = True
        super().on_unmount()

    def build(self) -> Widget:
        return self


class _BackCancelWidget(_FlagWidget):
    def __init__(self) -> None:
        super().__init__()
        self.back_called = False

    def handle_back_event(self) -> bool:
        self.back_called = True
        return False


@dataclass(frozen=True, slots=True)
class _GoIntent:
    name: str


@dataclass(frozen=True, slots=True)
class _AnimatedSpec:
    """A transition the navigator treats as animated: anything but the empty spec."""


def test_navigator_of_not_found_raises() -> None:
    # Attached, so the failure really is a missing provider; a bare unattached
    # Widget would (correctly) report the pre-mount case instead. With no Window
    # above it either, there is no fallback to reach for.
    w = Widget()
    Container().add_child(w)
    with pytest.raises(RuntimeError, match="not attached to a Window"):
        Navigator.of(w)


def test_navigator_of_before_mount_reports_premature() -> None:
    with pytest.raises(RuntimeError, match="before it was mounted"):
        Navigator.of(Widget())


def test_navigator_push_intent_resolves_widget() -> None:
    nav = Navigator.intents(
        initial=_GoIntent("home"),
        routes={_GoIntent: lambda i: _FlagWidget()},
    )

    nav.push(_GoIntent("x"))
    assert nav.can_pop() is True


def test_navigator_push_intent_resolves_widget_with_transition() -> None:
    spec = _AnimatedSpec()
    nav = Navigator.intents(
        initial=_GoIntent("home"),
        routes={_GoIntent: lambda i: (_FlagWidget(), spec)},
    )

    nav.push(_GoIntent("x"))
    assert nav._stack.elements[-1].transition is spec


def test_navigator_push_intent_with_transition_raises() -> None:
    nav = Navigator.intents(
        initial=_GoIntent("home"),
        routes={_GoIntent: lambda i: _FlagWidget()},
    )

    with pytest.raises(TypeError, match=r"transition= applies to a widget"):
        nav.push(_GoIntent("x"), transition=Transitions.empty())


def test_navigator_push_widget_keeps_its_transition() -> None:
    spec = _AnimatedSpec()
    nav = Navigator(_FlagWidget())

    nav.push(_FlagWidget(), transition=spec)

    assert nav._stack.elements[-1].transition is spec


def test_core_navigator_default_transition_is_none() -> None:
    nav = Navigator(_FlagWidget())

    nav.push(_FlagWidget())

    assert isinstance(nav._stack.elements[-1].transition, EmptyTransitionSpec)


def test_material_navigator_default_transition_is_the_page() -> None:
    nav = MaterialNavigator(_FlagWidget())

    nav.push(_FlagWidget())

    assert isinstance(nav._stack.elements[-1].transition, MaterialTransitionSpec)


def test_navigator_stack_yields_widgets_without_mounting() -> None:
    bottom, top = _FlagWidget(), _FlagWidget()
    nav = Navigator.routes([bottom, top])

    assert nav.stack == (bottom, top)
    assert nav.children_snapshot() == []


def test_navigator_push_unknown_intent_raises() -> None:
    nav = Navigator(_FlagWidget())

    with pytest.raises(RuntimeError, match=r"No route is registered for intent: _GoIntent"):
        nav.push(_GoIntent("x"))


def test_navigator_normalize_to_route_wraps_widget() -> None:
    nav = Navigator(_FlagWidget())
    widget = _FlagWidget()

    normalized = nav._normalize_to_route(widget, None)

    assert isinstance(normalized, Route)
    assert normalized.widget is widget


def test_navigator_normalize_to_route_resolves_intent() -> None:
    nav = Navigator.intents(
        initial=_GoIntent("home"),
        routes={_GoIntent: lambda _i: _FlagWidget()},
    )

    normalized = nav._normalize_to_route(_GoIntent("x"), None)

    assert isinstance(normalized, Route)


@pytest.mark.asyncio
async def test_navigator_request_back_is_canceled_by_top_widget_handler() -> None:
    bottom = _FlagWidget()
    top_widget = _BackCancelWidget()

    nav = Navigator(bottom)
    nav.push(top_widget)

    assert nav.can_pop() is True

    handled = await nav.request_back()
    assert handled is True
    assert nav.can_pop() is True
    assert top_widget.back_called is True


@pytest.mark.asyncio
async def test_navigator_popped_widget_is_unmounted() -> None:
    nav = Navigator(_FlagWidget())
    top_widget = _FlagWidget()
    nav.push(top_widget)

    assert nav.can_pop() is True
    assert await nav.request_back() is True
    assert nav.can_pop() is False
    assert top_widget.unmounted is True
