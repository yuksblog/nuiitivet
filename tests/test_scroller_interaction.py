"""Interaction tests for Scroller + Scrollbar.

These tests exercise mixed interactions such as dragging the scrollbar thumb
and then performing other pointer actions (e.g., pressing the content /
swiping) to reproduce and assert correct state transitions.

Note: These tests intentionally assert the *desired* behavior: pressing the
content while the scrollbar is actively dragging should not leave the
scrollbar in a dragging state or start a concurrent content drag. If the
current implementation exhibits the buggy behavior, the test will fail and
help locate the regression.
"""

from nuiitivet.scrolling import ScrollController
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.layout.scroller import Scroller
from nuiitivet.layout.column import Column
from nuiitivet.widgets.text import TextBase as Text
from tests.helpers.pointer import send_pointer_event_for_test_via_app_routing


def _make_basic_scroller():
    controller = ScrollController()
    controller._update_metrics(max_extent=300.0, viewport_size=200, content_size=500)
    child = Column([Text(f"Item {i}") for i in range(20)])
    scroller = Scroller(
        child=child,
        scroll_controller=controller,
        scrollbar_thickness=20,
        scrollbar_padding=0,
    )
    scroller.layout(200, 200)
    scroller.set_last_rect(0, 0, 200, 200)
    if scroller._scrollbar:
        scroller._scrollbar.set_last_rect(180, 0, 20, 200)
        scroller._scrollbar.thumb_rect = (180, 80, 20, 40)
    return (scroller, controller)


def test_press_scrollbar_then_press_content_should_cancel_scrollbar_drag():
    """Pressing the content while the scrollbar is dragging should cancel
    the scrollbar drag and not start a concurrent content drag.

    This test asserts the expected behavior. If the implementation leaves
    both scrollbar._dragging and scroller._is_dragging True, the test will
    fail and point to the interaction bug described by the user.
    """
    scroller, controller = _make_basic_scroller()
    scrollbar = scroller._scrollbar
    assert scrollbar is not None
    pressed_on_thumb = send_pointer_event_for_test_via_app_routing(
        scroller, PointerEventType.PRESS, 185, 90, pointer_id=1
    )
    assert pressed_on_thumb is True
    assert getattr(scrollbar, "_dragging", False) is True
    pressed_on_content = send_pointer_event_for_test_via_app_routing(
        scroller, PointerEventType.PRESS, 50, 50, pointer_id=2
    )
    assert pressed_on_content is True
    assert getattr(scrollbar, "_dragging", False) is False, "Scrollbar should stop dragging when content is pressed"
    assert scroller._is_dragging is True
