"""Raw pointer-stream node backing ``pointer_input()``.

Exercises ``PointerListenerNode`` at the node level: local coordinates, button
filtering, capture on/off, the individual press/move/release/enter/leave/scroll
callbacks, and ``on_modifier_keys_change`` delivery gating.
"""

from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_RIGHT, MOD_ALT, MOD_CTRL
from nuiitivet.input.pointer import PointerEvent, PointerEventType as T
from nuiitivet.widgets.interaction import PointerListenerNode

# x, y, w, h — a widget whose top-left is (10, 20).
_BOUNDS = (10, 20, 100, 40)


def _ev(et, x, y, **kw):
    return PointerEvent.mouse_event(1, et, x, y, **kw)


def test_press_inside_populates_widget_local_coords():
    seen = []
    node = PointerListenerNode(on_press=lambda e: seen.append((e.local_x, e.local_y)), capture=False)
    node.handle_pointer_event(_ev(T.PRESS, 30, 55, button=BUTTON_LEFT), _BOUNDS)
    # local = screen - widget top-left = (30-10, 55-20)
    assert seen == [(20.0, 35.0)]


def test_press_outside_bounds_is_ignored():
    seen = []
    node = PointerListenerNode(on_press=lambda e: seen.append(1), capture=False)
    assert node.handle_pointer_event(_ev(T.PRESS, 5, 5, button=BUTTON_LEFT), _BOUNDS) is False
    assert seen == []


def test_button_filter_suppresses_nonmatching_press():
    presses = []
    node = PointerListenerNode(
        on_press=lambda e: presses.append(e.button), buttons=(BUTTON_LEFT,), capture=False
    )
    assert node.handle_pointer_event(_ev(T.PRESS, 30, 55, button=BUTTON_RIGHT), _BOUNDS) is False
    assert presses == []
    node.handle_pointer_event(_ev(T.PRESS, 30, 55, button=BUTTON_LEFT), _BOUNDS)
    assert presses == [BUTTON_LEFT]


def test_capture_true_delivers_move_and_release_outside():
    moves, releases = [], []
    node = PointerListenerNode(
        on_move=lambda e: moves.append((e.local_x, e.local_y)),
        on_release=lambda e: releases.append(1),
        capture=True,
    )
    node.handle_pointer_event(_ev(T.PRESS, 30, 55, button=BUTTON_LEFT), _BOUNDS)
    # A move well outside the bounds still arrives because the pointer is captured.
    node.handle_pointer_event(_ev(T.MOVE, 500, 500, buttons=BUTTON_LEFT), _BOUNDS)
    assert moves == [(490.0, 480.0)]
    node.handle_pointer_event(_ev(T.RELEASE, 500, 500, button=BUTTON_LEFT), _BOUNDS)
    assert releases == [1]


def test_capture_false_suppresses_move_outside():
    moves = []
    node = PointerListenerNode(on_move=lambda e: moves.append(1), capture=False)
    node.handle_pointer_event(_ev(T.PRESS, 30, 55, button=BUTTON_LEFT), _BOUNDS)
    node.handle_pointer_event(_ev(T.MOVE, 500, 500, buttons=BUTTON_LEFT), _BOUNDS)
    assert moves == []
    # A move that stays inside still reports.
    node.handle_pointer_event(_ev(T.MOVE, 40, 55, buttons=BUTTON_LEFT), _BOUNDS)
    assert moves == [1]


def test_move_carries_held_button_mask():
    seen = []
    node = PointerListenerNode(on_move=lambda e: seen.append(e.buttons), capture=False)
    node.handle_pointer_event(_ev(T.MOVE, 30, 55, buttons=BUTTON_LEFT), _BOUNDS)
    assert seen == [BUTTON_LEFT]


def test_enter_leave_callbacks():
    events = []
    node = PointerListenerNode(
        on_enter=lambda e: events.append("enter"),
        on_leave=lambda e: events.append("leave"),
    )
    node.handle_pointer_event(_ev(T.ENTER, 30, 55), _BOUNDS)
    node.handle_pointer_event(_ev(T.LEAVE, 30, 55), _BOUNDS)
    assert events == ["enter", "leave"]


def test_scroll_callback():
    scrolls = []
    node = PointerListenerNode(on_scroll=lambda e: scrolls.append((e.scroll_x, e.scroll_y)))
    node.handle_pointer_event(PointerEvent.scroll_event(1, 30, 55, 0.0, 2.0), _BOUNDS)
    assert scrolls == [(0.0, 2.0)]


def test_modifier_change_fires_while_inside():
    seen = []
    node = PointerListenerNode(on_modifier_keys_change=lambda e: seen.append(e.modifier_keys))
    node.handle_pointer_event(_ev(T.ENTER, 30, 55), _BOUNDS)
    assert node.handle_modifier_keys_change(_ev(T.MOVE, 30, 55, modifier_keys=MOD_ALT), _BOUNDS) is True
    assert seen == [MOD_ALT]


def test_modifier_change_fires_while_captured_outside():
    seen = []
    node = PointerListenerNode(
        on_modifier_keys_change=lambda e: seen.append(e.modifier_keys), capture=True
    )
    node.handle_pointer_event(_ev(T.PRESS, 30, 55, button=BUTTON_LEFT), _BOUNDS)
    # Pointer is now conceptually outside but still captured.
    assert (
        node.handle_modifier_keys_change(_ev(T.MOVE, 500, 500, modifier_keys=MOD_CTRL), _BOUNDS)
        is True
    )
    assert seen == [MOD_CTRL]


def test_modifier_change_suppressed_when_neither_inside_nor_captured():
    seen = []
    node = PointerListenerNode(on_modifier_keys_change=lambda e: seen.append(1))
    assert (
        node.handle_modifier_keys_change(_ev(T.MOVE, 30, 55, modifier_keys=MOD_ALT), _BOUNDS)
        is False
    )
    assert seen == []


def test_modifier_change_stops_after_leave():
    seen = []
    node = PointerListenerNode(on_modifier_keys_change=lambda e: seen.append(1))
    node.handle_pointer_event(_ev(T.ENTER, 30, 55), _BOUNDS)
    node.handle_pointer_event(_ev(T.LEAVE, 30, 55), _BOUNDS)
    assert (
        node.handle_modifier_keys_change(_ev(T.MOVE, 30, 55, modifier_keys=MOD_ALT), _BOUNDS)
        is False
    )
    assert seen == []
