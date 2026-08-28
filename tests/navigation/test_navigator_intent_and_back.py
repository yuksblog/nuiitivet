"""Tests for Navigator intent resolution and back handling."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.navigation import Navigator, Route
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
        initial_route=_GoIntent("home"),
        routes={_GoIntent: lambda i: _FlagWidget()},
    )

    nav.push(_GoIntent("x"))
    assert nav.can_pop() is True


def test_navigator_push_intent_resolves_route() -> None:
    nav = Navigator.intents(
        initial_route=_GoIntent("home"),
        routes={_GoIntent: lambda i: Route(builder=_FlagWidget)},
    )

    nav.push(_GoIntent("x"))
    assert nav.can_pop() is True


def test_navigator_push_unknown_intent_raises() -> None:
    nav = Navigator(Route(builder=_FlagWidget))

    with pytest.raises(RuntimeError, match=r"No route is registered for intent: _GoIntent"):
        nav.push(_GoIntent("x"))


def test_navigator_normalize_to_route_passes_route_through() -> None:
    nav = Navigator(Route(builder=_FlagWidget))
    route = Route(builder=_FlagWidget)

    normalized = nav._normalize_to_route(route)

    assert normalized is route


def test_navigator_normalize_to_route_wraps_widget() -> None:
    nav = Navigator(Route(builder=_FlagWidget))
    widget = _FlagWidget()

    normalized = nav._normalize_to_route(widget)

    assert isinstance(normalized, Route)
    assert normalized is not widget
    assert normalized.build_widget() is widget


def test_navigator_normalize_to_route_resolves_intent() -> None:
    nav = Navigator.intents(
        initial_route=_GoIntent("home"),
        routes={_GoIntent: lambda _i: _FlagWidget()},
    )

    normalized = nav._normalize_to_route(_GoIntent("x"))

    assert isinstance(normalized, Route)


@pytest.mark.asyncio
async def test_navigator_request_back_is_canceled_by_top_widget_handler() -> None:
    bottom = Route(builder=_FlagWidget)
    top_widget = _BackCancelWidget()

    nav = Navigator(bottom)
    nav.push(top_widget)

    assert nav.can_pop() is True

    handled = await nav.request_back()
    assert handled is True
    assert nav.can_pop() is True
    assert top_widget.back_called is True


@pytest.mark.asyncio
async def test_navigator_push_widget_and_route_have_same_pop_behavior() -> None:
    nav_widget = Navigator(Route(builder=_FlagWidget))
    top_widget = _FlagWidget()
    nav_widget.push(top_widget)

    assert nav_widget.can_pop() is True
    assert await nav_widget.request_back() is True
    assert nav_widget.can_pop() is False
    assert top_widget.unmounted is True

    nav_route = Navigator(Route(builder=_FlagWidget))
    top_route_widget = _FlagWidget()
    nav_route.push(Route(builder=lambda: top_route_widget))

    assert nav_route.can_pop() is True
    assert await nav_route.request_back() is True
    assert nav_route.can_pop() is False
    assert top_route_widget.unmounted is True
