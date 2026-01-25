"""Extended interaction tests for Scroller + Scrollbar.

These tests exercise additional mixed interactions to catch ordering and
state-transition bugs when multiple input sequences occur.
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
    scroller.set_last_rect(0, 0, 200, 200)
    if scroller._scrollbar:
        scroller._scrollbar.set_last_rect(180, 0, 20, 200)
        scroller._scrollbar.thumb_rect = (180, 80, 20, 40)
    return (scroller, controller)


def test_drag_scrollbar_then_move_outside_should_not_start_content_drag():
    """While dragging the scrollbar, moving the pointer over content
    should be forwarded to the scrollbar (thumb drag) and should not
    start a content drag.
    """
    scroller, controller = _make_basic_scroller()
    sb = scroller._scrollbar
    assert sb is not None
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.PRESS, 185, 90, pointer_id=1) is True
    assert getattr(sb, "_dragging", False) is True
    prev_offset = controller.get_offset(sb.direction)
    handled = send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.MOVE, 50, 100, pointer_id=1)
    assert handled is True
    assert getattr(sb, "_dragging", False) is True
    assert controller.get_offset(sb.direction) != prev_offset
    assert scroller._is_dragging is False


def test_drag_scrollbar_then_release_then_start_content_drag():
    """After releasing the scrollbar, pressing content should start a
    content drag.
    """
    scroller, controller = _make_basic_scroller()
    sb = scroller._scrollbar
    assert sb is not None
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.PRESS, 185, 90, pointer_id=1) is True
    assert getattr(sb, "_dragging", False) is True
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.MOVE, 185, 110, pointer_id=1) is True
    assert (
        send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.RELEASE, 185, 110, pointer_id=1) is True
    )
    assert getattr(sb, "_dragging", False) is False
    pressed = send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.PRESS, 50, 50, pointer_id=1)
    assert pressed is True
    assert scroller._is_dragging is True
    prev = controller.get_offset(scroller.direction)
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.MOVE, 50, 40, pointer_id=1) is True
    assert controller.get_offset(scroller.direction) != prev


def test_drag_content_then_press_scrollbar_should_switch_to_scrollbar_drag():
    """If the user is dragging content and then presses the scrollbar,
    the content drag should be cancelled and the scrollbar drag should
    begin.

    Note: this documents the desired behavior. If the current
    implementation doesn't perform the cancellation, the test will fail
    and signal a second interaction issue to address.
    """
    scroller, controller = _make_basic_scroller()
    sb = scroller._scrollbar
    assert sb is not None
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.PRESS, 50, 150, pointer_id=1) is True
    assert scroller._is_dragging is True
    pressed_on_thumb = send_pointer_event_for_test_via_app_routing(
        scroller, PointerEventType.PRESS, 185, 90, pointer_id=2
    )
    assert pressed_on_thumb is True
    assert getattr(sb, "_dragging", False) is True, "Scrollbar should start dragging after thumb press"
    assert scroller._is_dragging is False, "Content drag should be cancelled when pressing scrollbar"


def test_scrollbar_drag_release_from_other_pointer_should_not_cancel():
    scroller, controller = _make_basic_scroller()
    sb = scroller._scrollbar
    assert sb is not None
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.PRESS, 185, 90, pointer_id=1) is True
    assert getattr(sb, "_dragging", False) is True
    prev = controller.get_offset(sb.direction)
    assert (
        send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.RELEASE, 185, 90, pointer_id=2) is False
    )
    assert getattr(sb, "_dragging", False) is True
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.MOVE, 185, 120, pointer_id=1) is True
    assert controller.get_offset(sb.direction) != prev


def test_content_drag_release_from_other_pointer_should_not_cancel():
    scroller, _ = _make_basic_scroller()
    assert send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.PRESS, 50, 120, pointer_id=1) is True
    assert scroller._is_dragging is True
    assert (
        send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.RELEASE, 60, 110, pointer_id=2) is False
    )
    assert scroller._is_dragging is True
    assert (
        send_pointer_event_for_test_via_app_routing(scroller, PointerEventType.RELEASE, 60, 110, pointer_id=1) is True
    )
    assert scroller._is_dragging is False
