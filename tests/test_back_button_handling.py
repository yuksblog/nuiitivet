from __future__ import annotations

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


def test_escape_closes_overlay_before_navigator_pop() -> None:
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()
    navigator.push(Container())
    overlay.show(Container(width=100, height=100))

    assert overlay.has_entries() is True
    assert navigator.can_pop() is True

    handled = app._dispatch_key_press("escape")
    assert handled is True
    assert overlay.has_entries() is False
    assert navigator.can_pop() is True


def test_escape_pops_navigator_when_no_overlay_entries() -> None:
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()
    navigator.push(Container())

    assert overlay.has_entries() is False
    assert navigator.can_pop() is True

    handled = app._dispatch_key_press("escape")
    assert handled is True
    assert navigator.can_pop() is False


def test_back_event_is_unhandled_when_nothing_to_pop_or_close() -> None:
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()

    assert overlay.has_entries() is False
    assert navigator.can_pop() is False

    assert app.can_handle_back_event() is False
    assert app.handle_back_event() is False


def test_escape_respects_will_pop_cancel() -> None:
    cancel_pop = will_pop(on_will_pop=lambda: False)
    app = App(content=Container())
    overlay = Overlay.root()
    navigator = Navigator.root()
    navigator.push(Container().modifier(cancel_pop))

    assert overlay.has_entries() is False
    assert navigator.can_pop() is True

    handled = app._dispatch_key_press("escape")
    assert handled is True
    assert navigator.can_pop() is True


def test_back_queue_pops_multiple_routes_even_during_transition() -> None:
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container())
    navigator.push(Container())
    navigator.push(Container())

    assert navigator.can_pop() is True

    assert app.handle_back_event() is True
    assert app.handle_back_event() is True
    assert app.handle_back_event() is True

    _force_finish_all_pop_transitions(navigator)
    assert navigator.can_pop() is False


def test_back_queue_is_cleared_when_will_pop_cancels_midway() -> None:
    cancel_pop = will_pop(on_will_pop=lambda: False)
    app = App(content=Container())
    navigator = Navigator.root()
    navigator.push(Container())
    navigator.push(Container().modifier(cancel_pop))

    assert navigator.can_pop() is True

    # First back pops top -> middle (allowed). Second back should be canceled by will_pop on middle.
    assert app.handle_back_event() is True
    assert app.handle_back_event() is True

    _force_finish_all_pop_transitions(navigator)
    assert navigator.can_pop() is True

    # Further backs stay canceled.
    assert app.handle_back_event() is True
    _force_finish_all_pop_transitions(navigator)
    assert navigator.can_pop() is True
