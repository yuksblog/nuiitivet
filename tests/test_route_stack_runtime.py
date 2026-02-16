from __future__ import annotations

from nuiitivet.navigation.route import Route
from nuiitivet.navigation.stack_runtime import EntryLifecycle, RouteStackRuntime
from nuiitivet.navigation.transition_spec import Transitions
from nuiitivet.widgeting.widget import Widget


class _DummyWidget(Widget):
    pass


def _make_route() -> Route:
    return Route(builder=_DummyWidget, transition_spec=Transitions.empty())


def test_push_sets_entering_then_active() -> None:
    base = _make_route()
    runtime = RouteStackRuntime(initial_routes=[base], pinned_routes=[base])
    route = _make_route()

    entry = runtime.push(route)
    assert entry.state is EntryLifecycle.ENTERING

    changed = runtime.mark_active(route)
    assert changed is True
    assert runtime.entries[-1].state is EntryLifecycle.ACTIVE


def test_begin_pop_sets_exiting_and_complete_exit_disposes() -> None:
    base = _make_route()
    route = _make_route()
    runtime = RouteStackRuntime(initial_routes=[base, route], pinned_routes=[base])

    popped = runtime.begin_pop()
    assert popped is route
    assert runtime.entries[-1].state is EntryLifecycle.EXITING

    completed = runtime.complete_exit(route)
    assert completed is True
    assert len(runtime.routes) == 1
    assert runtime.top() is base


def test_pinned_route_cannot_pop() -> None:
    base = _make_route()
    runtime = RouteStackRuntime(initial_routes=[base], pinned_routes=[base])

    assert runtime.can_pop(min_routes=1) is False
    assert runtime.begin_pop() is None


def test_remove_marks_exit_and_disposes() -> None:
    base = _make_route()
    route = _make_route()
    runtime = RouteStackRuntime(initial_routes=[base, route], pinned_routes=[base])

    removed = runtime.remove(route)
    assert removed is True
    assert len(runtime.routes) == 1
    assert runtime.top() is base
