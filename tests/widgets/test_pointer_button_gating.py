"""Node-level pointer button gating.

Only a primary (left / synthetic) button activates a click or starts a drag;
secondary buttons must not. A release from a different button than the one that
opened the press must not terminate the interaction.
"""

from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT, MOD_SHIFT
from nuiitivet.input.pointer import PointerEvent, PointerEventType as T
from nuiitivet.widgets.interaction import DraggableNode, InteractionState, PointerInputNode

_BOUNDS = (0, 0, 100, 40)


def _press_release(node, button):
    for et in (T.PRESS, T.RELEASE):
        node.handle_pointer_event(PointerEvent.mouse_event(1, et, 10, 10, button=button), _BOUNDS)


def test_only_primary_button_fires_click():
    results = {}
    for label, btn in [("left", BUTTON_LEFT), ("right", BUTTON_RIGHT), ("middle", BUTTON_MIDDLE), ("none", None)]:
        clicks = []
        node = PointerInputNode()
        node.enable_click(on_click=lambda: clicks.append(1))
        _press_release(node, btn)
        results[label] = len(clicks)

    assert results["left"] == 1
    assert results["none"] == 1  # synthetic / touch still activates
    assert results["right"] == 0
    assert results["middle"] == 0


def test_modifiers_reach_press_callback():
    seen = []
    node = PointerInputNode()
    node.enable_click(on_press=lambda e: seen.append(e.modifier_keys))
    node.handle_pointer_event(
        PointerEvent.mouse_event(1, T.PRESS, 10, 10, button=BUTTON_LEFT, modifier_keys=MOD_SHIFT),
        _BOUNDS,
    )
    assert seen == [MOD_SHIFT]


def test_secondary_release_does_not_end_left_press():
    clicks = []
    node = PointerInputNode(state=InteractionState())
    node.enable_click(on_click=lambda: clicks.append(1))

    # Left press opens the interaction.
    assert node.handle_pointer_event(PointerEvent.mouse_event(1, T.PRESS, 10, 10, button=BUTTON_LEFT), _BOUNDS)
    assert node.state.pressed is True

    # A right release (same shared pointer id) must be ignored.
    handled = node.handle_pointer_event(PointerEvent.mouse_event(1, T.RELEASE, 10, 10, button=BUTTON_RIGHT), _BOUNDS)
    assert handled is False
    assert node.state.pressed is True
    assert clicks == []

    # The matching left release completes the click.
    assert node.handle_pointer_event(PointerEvent.mouse_event(1, T.RELEASE, 10, 10, button=BUTTON_LEFT), _BOUNDS)
    assert node.state.pressed is False
    assert clicks == [1]


def test_draggable_only_primary_starts_drag():
    for btn, expected in [(BUTTON_LEFT, True), (BUTTON_RIGHT, False), (BUTTON_MIDDLE, False), (None, True)]:
        starts = []
        node = DraggableNode(on_drag_start=lambda e: starts.append(1))
        handled = node.handle_pointer_event(PointerEvent.mouse_event(1, T.PRESS, 10, 10, button=btn), _BOUNDS)
        assert handled is expected
        assert bool(starts) is expected


def test_draggable_secondary_release_does_not_end_drag():
    events = []
    node = DraggableNode(
        on_drag_start=lambda e: events.append("start"),
        on_drag_end=lambda e: events.append("end"),
    )
    node.handle_pointer_event(PointerEvent.mouse_event(1, T.PRESS, 10, 10, button=BUTTON_LEFT), _BOUNDS)
    assert events == ["start"]

    # A right release must not end the left drag.
    handled = node.handle_pointer_event(PointerEvent.mouse_event(1, T.RELEASE, 10, 10, button=BUTTON_RIGHT), _BOUNDS)
    assert handled is False
    assert events == ["start"]

    # The matching left release ends it.
    node.handle_pointer_event(PointerEvent.mouse_event(1, T.RELEASE, 10, 10, button=BUTTON_LEFT), _BOUNDS)
    assert events == ["start", "end"]
