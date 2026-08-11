from __future__ import annotations

from typing import Any

import pytest

from nuiitivet.modifiers import will_pop
from nuiitivet.navigation import Navigator, Route
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def __init__(self, *, label: str = "") -> None:
        super().__init__()
        self.label = label
        self.unmounted = False

    def on_unmount(self) -> None:
        self.unmounted = True
        super().on_unmount()

    def build(self) -> Widget:
        return self


@pytest.mark.asyncio
async def test_will_pop_modifier_chains_inner_to_outer() -> None:
    calls: list[str] = []

    def inner() -> bool:
        calls.append("inner")
        return True

    def outer() -> bool:
        calls.append("outer")
        return True

    w = _FlagWidget().modifier(will_pop(inner) | will_pop(outer))
    handler = getattr(w, "handle_back_event", None)
    assert callable(handler)
    result = await handler()
    assert result is True
    assert calls == ["inner", "outer"]


async def test_navigator_pop_respects_will_pop_cancel(nuiitivet_mount) -> None:
    calls: list[str] = []
    outgoing = _FlagWidget(label="outgoing")

    def on_will_pop() -> bool:
        calls.append("called")
        return False

    nav = Navigator.routes(
        [
            Route(builder=lambda: _FlagWidget(label="root")),
            Route(builder=lambda: outgoing.modifier(will_pop(on_will_pop))),
        ]
    )

    host = nuiitivet_mount(nav)
    host.layout(200, 100)
    assert nav.can_pop() is True

    nav.pop()
    await host.idle()

    assert nav.can_pop() is True
    assert outgoing.unmounted is False
    assert calls == ["called"]


async def test_navigator_pop_respects_will_pop_allow(nuiitivet_mount) -> None:
    outgoing = _FlagWidget(label="outgoing")

    def on_will_pop() -> bool:
        return True

    nav = Navigator.routes(
        [
            Route(builder=lambda: _FlagWidget(label="root")),
            Route(builder=lambda: outgoing.modifier(will_pop(on_will_pop))),
        ]
    )

    host = nuiitivet_mount(nav)
    host.layout(200, 100)
    assert nav.can_pop() is True

    nav.pop()
    await host.idle()

    assert nav.can_pop() is False


async def test_navigator_pop_calls_will_pop_inside_build(nuiitivet_mount) -> None:
    calls: list[str] = []

    from nuiitivet.widgeting.widget import ComposableWidget

    class Outgoing(ComposableWidget):
        def __init__(self) -> None:
            super().__init__()
            self.unmounted = False

        def on_unmount(self) -> None:
            self.unmounted = True
            super().on_unmount()

        def build(self) -> Widget:
            def on_will_pop() -> bool:
                calls.append("called")
                return False

            return Widget().modifier(will_pop(on_will_pop))

    outgoing = Outgoing()
    nav = Navigator.routes(
        [
            Route(builder=lambda: _FlagWidget(label="root")),
            Route(builder=lambda: outgoing),
        ]
    )

    host = nuiitivet_mount(nav)
    host.layout(200, 100)
    assert nav.can_pop() is True

    nav.pop()
    await host.idle()

    assert calls == ["called"]
    assert nav.can_pop() is True
    assert outgoing.unmounted is False


# ---------------------------------------------------------------------------
# Re-entrancy guard (#53)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reentrant_back_is_dropped_while_handler_is_active() -> None:
    """A re-entrant await handle_back_event during async on_will_pop is blocked."""
    calls: list[str] = []
    scope_ref: list[Any] = []

    async def on_will_pop() -> bool:
        calls.append("enter")
        # Simulate re-entrant call while _handling is True.
        scope = scope_ref[0]
        handler = getattr(scope, "handle_back_event", None)
        assert callable(handler)
        result = await handler()
        calls.append(f"reentrant={result}")
        return False

    w = _FlagWidget()
    scoped = w.modifier(will_pop(on_will_pop))
    scope_ref.append(scoped)

    handler = getattr(scoped, "handle_back_event", None)
    assert callable(handler)
    result = await handler()

    assert result is False
    assert calls == ["enter", "reentrant=False"]


@pytest.mark.asyncio
async def test_handling_flag_is_released_after_normal_return() -> None:
    """_handling must be False after a successful callback invocation."""
    scope_ref: list[Any] = []

    def on_will_pop() -> bool:
        return False

    w = _FlagWidget()
    scoped = w.modifier(will_pop(on_will_pop))
    scope_ref.append(scoped)

    handler = getattr(scoped, "handle_back_event", None)
    assert callable(handler)
    await handler()

    assert getattr(scoped, "_handling", True) is False


@pytest.mark.asyncio
async def test_handling_flag_is_released_after_exception() -> None:
    """_handling must be False even when the callback raises."""

    def on_will_pop() -> bool:
        raise RuntimeError("boom")

    w = _FlagWidget()
    scoped = w.modifier(will_pop(on_will_pop))

    handler = getattr(scoped, "handle_back_event", None)
    assert callable(handler)
    result = await handler()  # fail-open → True

    assert result is True
    assert getattr(scoped, "_handling", True) is False


async def test_normal_pop_allowed_works_after_previous_cancel(nuiitivet_mount) -> None:
    """After a cancelled pop, a subsequent allow should still propagate."""
    call_count = 0

    def on_will_pop() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count >= 2  # first call cancels, second allows

    nav = Navigator.routes(
        [
            Route(builder=lambda: _FlagWidget(label="root")),
            Route(builder=lambda: _FlagWidget(label="outgoing").modifier(will_pop(on_will_pop))),
        ]
    )
    host = nuiitivet_mount(nav)
    host.layout(200, 100)

    nav.pop()
    await host.idle()
    assert nav.can_pop() is True  # first pop was cancelled

    nav.pop()
    await host.idle()
    assert nav.can_pop() is False  # second pop was allowed
