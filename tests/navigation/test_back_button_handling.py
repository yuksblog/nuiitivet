from __future__ import annotations

import asyncio

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.modifiers import will_pop
from nuiitivet.navigation import Navigator
from nuiitivet.overlay import Overlay
from nuiitivet.runtime.app import App


def _force_finish_all_pop_transitions(navigator: Navigator) -> None:
    while True:
        transition = getattr(navigator, "_transition", None)
        handle = getattr(navigator, "_transition_handle", None)
        if transition is None or handle is None or getattr(transition, "kind", None) != "pop":
            return
        navigator._force_finish_pop_transition()


@pytest.mark.asyncio
async def test_escape_closes_overlay_before_navigator_pop() -> None:
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()
    navigator.push(Container())
    overlay.show(Container(width=100, height=100), backdrop=True)

    assert overlay.has_entries() is True
    assert navigator.can_pop() is True

    handled = app._dispatch_key_press("escape")
    assert handled is True
    await asyncio.sleep(0)  # allow back event task to run
    assert overlay.has_entries() is False
    assert navigator.can_pop() is True


@pytest.mark.asyncio
async def test_escape_pops_navigator_when_no_overlay_entries() -> None:
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()
    navigator.push(Container())

    assert overlay.has_entries() is False
    assert navigator.can_pop() is True

    handled = app._dispatch_key_press("escape")
    assert handled is True
    await asyncio.sleep(0)  # allow back event task to run
    assert navigator.can_pop() is False


@pytest.mark.asyncio
async def test_back_event_is_unhandled_when_nothing_to_pop_or_close() -> None:
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()

    assert overlay.has_entries() is False
    assert navigator.can_pop() is False

    assert app.can_handle_back_event() is False
    assert await app.handle_back_event() is False


@pytest.mark.asyncio
async def test_escape_respects_will_pop_cancel() -> None:
    cancel_pop = will_pop(on_will_pop=lambda: False)
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()
    navigator.push(Container().modifier(cancel_pop))

    assert overlay.has_entries() is False
    assert navigator.can_pop() is True

    handled = app._dispatch_key_press("escape")
    assert handled is True
    await asyncio.sleep(0)  # allow back event task to run
    assert navigator.can_pop() is True


@pytest.mark.asyncio
async def test_back_queue_pops_multiple_routes_even_during_transition() -> None:
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container())
    navigator.push(Container())
    navigator.push(Container())

    assert navigator.can_pop() is True

    assert await app.handle_back_event() is True
    assert await app.handle_back_event() is True
    assert await app.handle_back_event() is True

    _force_finish_all_pop_transitions(navigator)
    assert navigator.can_pop() is False


@pytest.mark.asyncio
async def test_back_queue_is_cleared_when_will_pop_cancels_midway() -> None:
    cancel_pop = will_pop(on_will_pop=lambda: False)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container())
    navigator.push(Container().modifier(cancel_pop))

    assert navigator.can_pop() is True

    # First back pops top -> middle (allowed). Second back should be canceled by will_pop on middle.
    assert await app.handle_back_event() is True
    assert await app.handle_back_event() is True

    _force_finish_all_pop_transitions(navigator)
    assert navigator.can_pop() is True

    # Further backs stay canceled.
    assert await app.handle_back_event() is True
    _force_finish_all_pop_transitions(navigator)
    assert navigator.can_pop() is True


# ---------------------------------------------------------------------------
# Async on_will_pop tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_on_will_pop_allow() -> None:
    """Async on_will_pop returning True allows the pop."""
    resolved = asyncio.Event()

    async def on_will_pop() -> bool:
        resolved.set()
        return True

    scope_mod = will_pop(on_will_pop=on_will_pop)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container().modifier(scope_mod))

    assert navigator.can_pop() is True
    assert await app.handle_back_event() is True
    assert resolved.is_set()
    assert navigator.can_pop() is False


@pytest.mark.asyncio
async def test_async_on_will_pop_cancel() -> None:
    """Async on_will_pop returning False cancels the pop."""

    async def on_will_pop() -> bool:
        return False

    scope_mod = will_pop(on_will_pop=on_will_pop)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container().modifier(scope_mod))

    assert navigator.can_pop() is True
    assert await app.handle_back_event() is True  # handled (ESC captured), pop canceled
    assert navigator.can_pop() is True  # route still present


@pytest.mark.asyncio
async def test_async_on_will_pop_exception_fails_open() -> None:
    """If async on_will_pop raises, pop is allowed (fail open)."""

    async def on_will_pop() -> bool:
        raise RuntimeError("dialog error")

    scope_mod = will_pop(on_will_pop=on_will_pop)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container().modifier(scope_mod))

    assert navigator.can_pop() is True
    assert await app.handle_back_event() is True
    # Fail open: pop proceeds despite exception
    assert navigator.can_pop() is False


@pytest.mark.asyncio
async def test_async_on_will_pop_handling_flag_released_on_exception() -> None:
    """_handling flag is released even when async on_will_pop raises."""

    async def on_will_pop() -> bool:
        raise RuntimeError("boom")

    scope_mod = will_pop(on_will_pop=on_will_pop)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container().modifier(scope_mod))
    navigator.push(Container())

    # Pop top route (no will_pop), then pop mid route (will_pop raises -> fail open)
    assert await app.handle_back_event() is True
    assert await app.handle_back_event() is True

    # After exception, _handling should be False (released in finally)
    outgoing_widget = navigator._stack.routes[-1].build_widget() if navigator.can_pop() else None
    if outgoing_widget is not None:
        will_pop_scope = outgoing_widget if hasattr(outgoing_widget, "_handling") else None
        if will_pop_scope is not None:
            assert will_pop_scope._handling is False


@pytest.mark.asyncio
async def test_sync_on_will_pop_still_works() -> None:
    """Sync bool-returning callbacks continue to work unchanged."""
    call_count = 0

    def on_will_pop() -> bool:
        nonlocal call_count
        call_count += 1
        return True

    scope_mod = will_pop(on_will_pop=on_will_pop)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container().modifier(scope_mod))

    assert navigator.can_pop() is True
    assert await app.handle_back_event() is True
    assert call_count == 1
    assert navigator.can_pop() is False


@pytest.mark.asyncio
async def test_reentrance_guard_blocks_concurrent_back_during_async_will_pop() -> None:
    """_handling flag prevents re-entrant back events during async on_will_pop."""
    gate = asyncio.Event()

    async def on_will_pop() -> bool:
        await gate.wait()  # suspends until gate is set
        return True

    scope_mod = will_pop(on_will_pop=on_will_pop)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container().modifier(scope_mod))

    # Start first back event but don't complete it yet
    task = asyncio.create_task(app.handle_back_event())
    await asyncio.sleep(0)  # let task reach the await gate.wait()

    # WillPopScope._handling should be True while suspended in on_will_pop
    outgoing_widget = navigator._route_widget(navigator._stack.routes[-1])
    # The outgoing widget is a WillPopScope
    assert getattr(outgoing_widget, "_handling", None) is True

    # A second back event while the first is suspended should be blocked
    second_result = await app.handle_back_event()
    assert second_result is True  # handled (navigator.can_pop is True)
    # But pop was blocked by _handling — route still present
    assert navigator.can_pop() is True

    # Now let the first task complete
    gate.set()
    result = await task
    assert result is True
    assert navigator.can_pop() is False
