"""Unit tests for the standalone Scrollbar widget."""

from __future__ import annotations
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.widgets.scrollbar import Scrollbar, ScrollbarBehavior
from tests.helpers.pointer import send_pointer_event_for_test


class DummyApp:
    """Minimal app stub providing invalidate() for widget tests."""

    def __init__(self) -> None:
        self.invalidate_calls = 0

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidate_calls += 1


class DummyAnimationHandle:

    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class DummyAnimateApp(DummyApp):
    """App stub that also provides animate()."""

    def __init__(self) -> None:
        super().__init__()
        self.animate_calls = 0
        self.last_handle: DummyAnimationHandle | None = None

    def animate(self, **kwargs):
        del kwargs
        self.animate_calls += 1
        handle = DummyAnimationHandle()
        self.last_handle = handle
        return handle


def test_scrollbar_mounts_and_listens_to_controller() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    scrollbar = Scrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False))
    app = DummyApp()
    scrollbar.mount(app)
    assert scrollbar._offset_unsubscribe is not None
    before = scrollbar._last_interaction
    controller.axis_state(ScrollDirection.VERTICAL).offset.value = 25.0
    assert scrollbar._last_interaction >= before
    assert app.invalidate_calls >= 1
    scrollbar.unmount()
    assert scrollbar._offset_unsubscribe is None


def test_scrollbar_auto_hide_starts_animation_on_scroll() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=200.0, viewport_size=200, content_size=400)
    behavior = ScrollbarBehavior(auto_hide=True, hide_delay=0.01, fade_duration=0.01)
    scrollbar = Scrollbar(controller, behavior=behavior)
    app = DummyAnimateApp()
    scrollbar.mount(app)
    controller.axis_state(ScrollDirection.VERTICAL).offset.value = 10.0
    assert app.animate_calls == 1
    assert app.last_handle is not None
    handle = app.last_handle
    scrollbar.unmount()
    assert handle is not None
    assert handle.cancelled is True
    assert scrollbar._offset_unsubscribe is None


def test_scrollbar_drag_responds_to_mouse_move() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=400.0, viewport_size=200, content_size=600)
    scrollbar = Scrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False))
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, 40)
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, 10) is True
    assert scrollbar._dragging is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.MOVE, 2, 50) is True
    assert controller.get_offset() > 0.0
    assert send_pointer_event_for_test(scrollbar, PointerEventType.RELEASE, 2, 50) is True
    assert scrollbar._dragging is False


def test_scrollbar_horizontal_drag_responds_to_mouse_move() -> None:
    controller = ScrollController(axes=(ScrollDirection.HORIZONTAL,), primary_axis=ScrollDirection.HORIZONTAL)
    controller._update_metrics(max_extent=400.0, viewport_size=300, content_size=700)
    scrollbar = Scrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False), direction=ScrollDirection.HORIZONTAL)
    scrollbar.bar_rect = (0, 0, 200, scrollbar.thickness)
    scrollbar.thumb_rect = (0, 0, 60, scrollbar.thickness)
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 30, 2) is True
    assert scrollbar._dragging is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.MOVE, 80, 2) is True
    assert controller.get_offset(axis=ScrollDirection.HORIZONTAL) > 0.0
    assert send_pointer_event_for_test(scrollbar, PointerEventType.RELEASE, 80, 2) is True
    assert scrollbar._dragging is False


def test_hit_slop_expands_hover_and_press() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=400.0, viewport_size=200, content_size=600)
    behavior = ScrollbarBehavior(auto_hide=False)
    scrollbar = Scrollbar(controller, behavior=behavior)
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, 40)
    hs = max(8, scrollbar.thickness)
    outside_x = scrollbar.thickness + hs - 1
    outside_y = 10
    assert send_pointer_event_for_test(scrollbar, PointerEventType.MOVE, outside_x, outside_y) is True
    assert scrollbar._hovering is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, outside_x, outside_y) is True
    assert scrollbar._dragging is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.RELEASE, outside_x, outside_y) is True
    assert scrollbar._dragging is False


def test_hit_slop_expands_hover_and_press_horizontal() -> None:
    controller = ScrollController(axes=(ScrollDirection.HORIZONTAL,), primary_axis=ScrollDirection.HORIZONTAL)
    controller._update_metrics(max_extent=400.0, viewport_size=300, content_size=700)
    behavior = ScrollbarBehavior(auto_hide=False)
    scrollbar = Scrollbar(controller, behavior=behavior, direction=ScrollDirection.HORIZONTAL)
    scrollbar.bar_rect = (0, 0, 200, scrollbar.thickness)
    scrollbar.thumb_rect = (0, 0, 60, scrollbar.thickness)
    hs = max(8, scrollbar.thickness)
    outside_x = 10
    outside_y = scrollbar.thickness + hs - 1
    assert send_pointer_event_for_test(scrollbar, PointerEventType.MOVE, outside_x, outside_y) is True
    assert scrollbar._hovering is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, outside_x, outside_y) is True
    assert scrollbar._dragging is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.RELEASE, outside_x, outside_y) is True
    assert scrollbar._dragging is False


def test_track_click_behavior_page_vertical() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=400.0, viewport_size=100, content_size=500)
    controller.scroll_to(200.0)
    behavior = ScrollbarBehavior(auto_hide=False, track_click_behavior="page")
    scrollbar = Scrollbar(controller, behavior=behavior)
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 80, scrollbar.thickness, 40)
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, 50) is True
    assert controller.get_offset() == 100.0
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, 180) is True
    assert controller.get_offset() == 200.0


def test_track_click_behavior_jump_vertical() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=400.0, viewport_size=100, content_size=500)
    behavior = ScrollbarBehavior(auto_hide=False, track_click_behavior="jump")
    scrollbar = Scrollbar(controller, behavior=behavior)
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, 40)
    click_y = 150
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, click_y) is True
    expected = 0.75 * controller.axis_max_extent(ScrollDirection.VERTICAL)
    assert abs(controller.get_offset() - expected) < 50.0


def test_scrollbar_release_clears_hover_after_drag() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=300.0, viewport_size=150, content_size=450)
    scrollbar = Scrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False))
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, 40)
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, 10, pointer_id=1) is True
    assert scrollbar._dragging is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.MOVE, 200, 200, pointer_id=1) is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.RELEASE, 200, 200, pointer_id=1) is True
    assert scrollbar._dragging is False
    assert scrollbar._thumb_hover is False
    assert scrollbar._bar_hover is False
