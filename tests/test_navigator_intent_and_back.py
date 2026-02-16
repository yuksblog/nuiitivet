"""Tests for Navigator intent resolution and back handling."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from nuiitivet.navigation import Navigator, PageRoute, Route
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


def test_navigator_root_not_set_raises() -> None:
    Navigator._root = None  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="Navigator root is not set"):
        Navigator.root()


def test_navigator_of_not_found_raises() -> None:
    w = Widget()
    with pytest.raises(RuntimeError, match="Navigator not found in ancestors"):
        Navigator.of(w)


def test_navigator_push_intent_resolves_widget() -> None:
    nav = Navigator(
        routes=[PageRoute(builder=_FlagWidget)],
        intent_routes={_GoIntent: lambda i: _FlagWidget()},
    )

    nav.push(_GoIntent("x"))
    assert nav.can_pop() is True


def test_navigator_push_intent_resolves_route() -> None:
    nav = Navigator(
        routes=[PageRoute(builder=_FlagWidget)],
        intent_routes={_GoIntent: lambda i: Route(builder=_FlagWidget)},
    )

    nav.push(_GoIntent("x"))
    assert nav.can_pop() is True


def test_navigator_push_unknown_intent_raises() -> None:
    nav = Navigator(routes=[PageRoute(builder=_FlagWidget)])

    with pytest.raises(RuntimeError, match=r"No route is registered for intent: _GoIntent"):
        nav.push(_GoIntent("x"))


def test_navigator_normalize_to_route_passes_route_through() -> None:
    nav = Navigator(routes=[PageRoute(builder=_FlagWidget)])
    route = Route(builder=_FlagWidget)

    normalized = nav._normalize_to_route(route)

    assert normalized is route


def test_navigator_normalize_to_route_wraps_widget() -> None:
    nav = Navigator(routes=[PageRoute(builder=_FlagWidget)])
    widget = _FlagWidget()

    normalized = nav._normalize_to_route(widget)

    assert isinstance(normalized, Route)
    assert normalized is not widget
    assert normalized.build_widget() is widget


def test_navigator_normalize_to_route_resolves_intent() -> None:
    nav = Navigator(
        routes=[PageRoute(builder=_FlagWidget)],
        intent_routes={_GoIntent: lambda _i: _FlagWidget()},
    )

    normalized = nav._normalize_to_route(_GoIntent("x"))

    assert isinstance(normalized, Route)


def test_navigator_request_back_is_canceled_by_top_widget_handler() -> None:
    bottom = PageRoute(builder=_FlagWidget)
    top_widget = _BackCancelWidget()

    nav = Navigator(routes=[bottom])
    nav.push(top_widget)

    assert nav.can_pop() is True

    handled = nav.request_back()
    assert handled is True
    assert nav.can_pop() is True
    assert top_widget.back_called is True


def test_navigator_push_widget_and_route_have_same_pop_behavior() -> None:
    nav_widget = Navigator(routes=[PageRoute(builder=_FlagWidget)])
    top_widget = _FlagWidget()
    nav_widget.push(top_widget)

    assert nav_widget.can_pop() is True
    assert nav_widget.request_back() is True
    assert nav_widget.can_pop() is False
    assert top_widget.unmounted is True

    nav_route = Navigator(routes=[PageRoute(builder=_FlagWidget)])
    top_route_widget = _FlagWidget()
    nav_route.push(Route(builder=lambda: top_route_widget))

    assert nav_route.can_pop() is True
    assert nav_route.request_back() is True
    assert nav_route.can_pop() is False
    assert top_route_widget.unmounted is True
