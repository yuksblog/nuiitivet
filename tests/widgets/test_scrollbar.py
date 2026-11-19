"""Unit tests for the standalone Scrollbar widget."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Generator

from nuiitivet.observable import runtime as observable_runtime
from nuiitivet.scrolling import ScrollbarBehavior, ScrollController, ScrollDirection
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.widgets.scrollbar import HorizontalScrollbar, VerticalScrollbar
from tests.helpers.pointer import send_pointer_event_for_test


class DummyApp:
    """Minimal app stub providing invalidate() for widget tests."""

    def __init__(self) -> None:
        self.invalidate_calls = 0

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidate_calls += 1


class _FakeClock:
    """Clock whose time moves only on ``advance()``; fires one-shots when due."""

    def __init__(self) -> None:
        self._now = 0.0
        self._once: list[tuple[float, Callable[[float], None]]] = []
        self._intervals: list[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        self._once.append((self._now + delay, fn))

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        del interval
        self._intervals.append(fn)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self._once = [(t, cb) for t, cb in self._once if cb != fn]
        self._intervals = [cb for cb in self._intervals if cb != fn]

    def advance(self, dt: float) -> None:
        self._now += dt
        due = [(t, cb) for t, cb in self._once if t <= self._now]
        self._once = [(t, cb) for t, cb in self._once if t > self._now]
        for _, cb in due:
            cb(dt)
        for cb in list(self._intervals):
            cb(dt)


@contextmanager
def _fake_clock() -> Generator[_FakeClock, None, None]:
    prev = observable_runtime.clock
    fake = _FakeClock()
    observable_runtime.set_clock(fake)
    try:
        yield fake
    finally:
        observable_runtime.set_clock(prev)


def _overflowing_controller() -> ScrollController:
    controller = ScrollController()
    controller._update_metrics(max_extent=200.0, viewport_size=200, content_size=400)
    return controller


def test_auto_hide_scrollbar_starts_hidden_after_mount() -> None:
    behavior = ScrollbarBehavior(auto_hide=True, hide_delay=1.0, fade_duration=0.0)
    with _fake_clock() as clock:
        scrollbar = VerticalScrollbar(_overflowing_controller(), behavior=behavior)
        scrollbar.mount(DummyApp())
        assert scrollbar._visibility.value == 0.0
        assert clock._once == []
        scrollbar.unmount()


def test_scrollbar_without_auto_hide_is_visible_after_mount() -> None:
    behavior = ScrollbarBehavior(auto_hide=False, hide_delay=1.0, fade_duration=0.0)
    with _fake_clock() as clock:
        scrollbar = VerticalScrollbar(_overflowing_controller(), behavior=behavior)
        scrollbar.mount(DummyApp())
        assert scrollbar._visibility.value == 1.0
        clock.advance(5.0)
        assert scrollbar._visibility.value == 1.0
        scrollbar.unmount()


def test_auto_hide_scrollbar_shows_on_scroll_then_hides_after_delay() -> None:
    controller = _overflowing_controller()
    behavior = ScrollbarBehavior(auto_hide=True, hide_delay=1.0, fade_duration=0.0)
    with _fake_clock() as clock:
        scrollbar = VerticalScrollbar(controller, behavior=behavior)
        scrollbar.mount(DummyApp())
        controller.axis_state(ScrollDirection.VERTICAL).offset.value = 10.0
        assert scrollbar._visibility.value == 1.0

        clock.advance(0.9)
        assert scrollbar._visibility.value == 1.0

        clock.advance(0.2)
        assert scrollbar._visibility.value == 0.0
        scrollbar.unmount()


def test_remounted_auto_hide_scrollbar_starts_hidden() -> None:
    controller = _overflowing_controller()
    behavior = ScrollbarBehavior(auto_hide=True, hide_delay=1.0, fade_duration=0.0)
    with _fake_clock() as clock:
        scrollbar = VerticalScrollbar(controller, behavior=behavior)
        scrollbar.mount(DummyApp())
        controller.axis_state(ScrollDirection.VERTICAL).offset.value = 10.0
        assert scrollbar._visibility.value == 1.0
        scrollbar.unmount()
        assert clock._once == []

        scrollbar.mount(DummyApp())
        assert scrollbar._visibility.value == 0.0
        scrollbar.unmount()


def test_scrollbar_mounts_and_listens_to_controller() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    scrollbar = VerticalScrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False))
    app = DummyApp()
    scrollbar.mount(app)
    assert scrollbar._offset_unsubscribe is not None
    controller.axis_state(ScrollDirection.VERTICAL).offset.value = 25.0
    assert app.invalidate_calls >= 1
    scrollbar.unmount()
    assert scrollbar._offset_unsubscribe is None


def test_scrollbar_auto_hide_starts_animation_on_scroll() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=200.0, viewport_size=200, content_size=400)
    behavior = ScrollbarBehavior(auto_hide=True, hide_delay=0.2, fade_duration=0.01)
    scrollbar = VerticalScrollbar(controller, behavior=behavior)
    app = DummyApp()
    scrollbar.mount(app)

    assert scrollbar._visibility.target == 0.0

    controller.axis_state(ScrollDirection.VERTICAL).offset.value = 10.0
    assert scrollbar._hide_armed
    assert scrollbar._visibility.target == 1.0

    scrollbar._on_hide_timer(0.2)
    assert scrollbar._visibility.target == 0.0

    scrollbar.unmount()
    assert scrollbar._offset_unsubscribe is None
    assert scrollbar._visibility_unsubscribe is None


def test_scrollbar_drag_responds_to_mouse_move() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=400.0, viewport_size=200, content_size=600)
    scrollbar = VerticalScrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False))
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
    scrollbar = HorizontalScrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False))
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
    scrollbar = VerticalScrollbar(controller, behavior=behavior)
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
    scrollbar = HorizontalScrollbar(controller, behavior=behavior)
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
    scrollbar = VerticalScrollbar(controller, behavior=behavior)
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
    scrollbar = VerticalScrollbar(controller, behavior=behavior)
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, 40)
    click_y = 150
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, click_y) is True
    expected = 0.75 * controller.axis_max_extent(ScrollDirection.VERTICAL)
    assert abs(controller.get_offset() - expected) < 50.0


def test_track_click_jump_centers_thumb_on_click_vertical() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=400.0, viewport_size=100, content_size=500)
    behavior = ScrollbarBehavior(auto_hide=False, track_click_behavior="jump")
    scrollbar = VerticalScrollbar(controller, behavior=behavior)
    track_len = 200
    thumb_len = 40
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, track_len)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, thumb_len)
    click_y = 100
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, click_y) is True
    max_offset = controller.axis_max_extent(ScrollDirection.VERTICAL)
    scroll_ratio = controller.get_offset() / max_offset
    thumb_center = (track_len - thumb_len) * scroll_ratio + thumb_len / 2
    assert abs(thumb_center - click_y) <= 1.0


def test_track_click_jump_centers_thumb_on_click_horizontal() -> None:
    controller = ScrollController(axes=(ScrollDirection.HORIZONTAL,), primary_axis=ScrollDirection.HORIZONTAL)
    controller._update_metrics(max_extent=400.0, viewport_size=100, content_size=500)
    behavior = ScrollbarBehavior(auto_hide=False, track_click_behavior="jump")
    scrollbar = HorizontalScrollbar(controller, behavior=behavior)
    track_len = 200
    thumb_len = 40
    scrollbar.bar_rect = (0, 0, track_len, scrollbar.thickness)
    scrollbar.thumb_rect = (0, 0, thumb_len, scrollbar.thickness)
    click_x = 120
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, click_x, 2) is True
    max_offset = controller.axis_max_extent(ScrollDirection.HORIZONTAL)
    scroll_ratio = controller.get_offset(axis=ScrollDirection.HORIZONTAL) / max_offset
    thumb_center = (track_len - thumb_len) * scroll_ratio + thumb_len / 2
    assert abs(thumb_center - click_x) <= 1.0


def test_track_click_jump_starts_drag() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=400.0, viewport_size=100, content_size=500)
    behavior = ScrollbarBehavior(auto_hide=False, track_click_behavior="jump")
    scrollbar = VerticalScrollbar(controller, behavior=behavior)
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, 40)
    # Press on empty track (not on the thumb) should jump AND begin a drag.
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, 100) is True
    assert scrollbar._dragging is True
    after_jump = controller.get_offset()
    # Continuing to move the pointer should keep scrolling as a drag.
    assert send_pointer_event_for_test(scrollbar, PointerEventType.MOVE, 2, 140) is True
    assert controller.get_offset() > after_jump
    assert send_pointer_event_for_test(scrollbar, PointerEventType.RELEASE, 2, 140) is True
    assert scrollbar._dragging is False


def test_scrollbar_release_clears_hover_after_drag() -> None:
    controller = ScrollController()
    controller._update_metrics(max_extent=300.0, viewport_size=150, content_size=450)
    scrollbar = VerticalScrollbar(controller, behavior=ScrollbarBehavior(auto_hide=False))
    scrollbar.bar_rect = (0, 0, scrollbar.thickness, 200)
    scrollbar.thumb_rect = (0, 0, scrollbar.thickness, 40)
    assert send_pointer_event_for_test(scrollbar, PointerEventType.PRESS, 2, 10, pointer_id=1) is True
    assert scrollbar._dragging is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.MOVE, 200, 200, pointer_id=1) is True
    assert send_pointer_event_for_test(scrollbar, PointerEventType.RELEASE, 200, 200, pointer_id=1) is True
    assert scrollbar._dragging is False
    assert scrollbar._thumb_hover is False
    assert scrollbar._bar_hover is False
