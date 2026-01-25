"""Tests for Scroller widget and ScrollController."""

import pytest
from nuiitivet.runtime.app import App
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.scrolling import ScrollController, ScrollDirection, ScrollPhysics
from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.scroller import Scroller
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.scrollbar import Scrollbar, ScrollbarBehavior
from tests.helpers.pointer import send_pointer_event_for_test


class DummyCanvas:

    def save(self):
        return None

    def restore(self):
        return None

    def clipRect(self, *_args, **_kwargs):
        return None


def set_axis_offset(
    controller: ScrollController,
    value: float,
    axis: ScrollDirection = ScrollDirection.VERTICAL,
) -> None:
    controller.axis_state(axis).offset.value = float(value)


def test_scroll_controller_initial_state():
    """ScrollController should initialize with correct default values."""
    controller = ScrollController()
    assert controller.get_offset() == 0.0
    assert controller.max_extent == 0.0
    assert controller.viewport_size == 0
    assert controller.content_size == 0
    assert controller.is_at_start is True
    assert controller.is_at_end is True


def test_scroll_controller_initial_offsets():
    """ScrollController should accept per-axis initial_offsets."""
    controller = ScrollController(initial_offsets={ScrollDirection.VERTICAL: 50.0})
    assert controller.get_offset() == 50.0


def test_scroll_controller_supports_multiple_axes():
    controller = ScrollController(
        axes=(ScrollDirection.VERTICAL, ScrollDirection.HORIZONTAL),
        primary_axis=ScrollDirection.HORIZONTAL,
        initial_offsets={ScrollDirection.HORIZONTAL: 25.0},
    )
    assert controller.axes == (ScrollDirection.VERTICAL, ScrollDirection.HORIZONTAL)
    assert controller.primary_axis is ScrollDirection.HORIZONTAL
    assert controller.get_offset() == 25.0
    assert controller.axis_state(ScrollDirection.VERTICAL).offset.value == 0.0
    assert controller.get_offset(ScrollDirection.HORIZONTAL) == 25.0


def test_scroll_controller_scroll_to():
    """scroll_to should update offset and clamp to valid range."""
    controller = ScrollController()
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    controller.scroll_to(50.0)
    assert controller.get_offset() == 50.0
    controller.scroll_to(150.0)
    assert controller.get_offset() == 100.0
    controller.scroll_to(-10.0)
    assert controller.get_offset() == 0.0


def test_scroll_controller_scroll_by():
    """scroll_by should add delta to current offset."""
    controller = ScrollController()
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    controller.scroll_to(20.0)
    controller.scroll_by(30.0)
    assert controller.get_offset() == 50.0
    controller.scroll_by(-10.0)
    assert controller.get_offset() == 40.0


def test_scroll_controller_scroll_to_start():
    """scroll_to_start should set offset to 0."""
    controller = ScrollController(initial_offsets={ScrollDirection.VERTICAL: 50.0})
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    controller.scroll_to_start()
    assert controller.get_offset() == 0.0


def test_scroll_controller_scroll_to_end():
    """scroll_to_end should set offset to max_extent."""
    controller = ScrollController()
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    controller.scroll_to_end()
    assert controller.get_offset() == 100.0


def test_scroll_controller_is_at_start():
    """is_at_start should return True when at position 0."""
    controller = ScrollController()
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    assert controller.is_at_start is True
    controller.scroll_to(10.0)
    assert controller.is_at_start is False


def test_scroll_controller_is_at_end():
    """is_at_end should return True when at max_extent."""
    controller = ScrollController()
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    controller.scroll_to_end()
    assert controller.is_at_end is True
    controller.scroll_to(50.0)
    assert controller.is_at_end is False


def test_scroll_controller_update_metrics():
    """_update_metrics should update all internal states."""
    controller = ScrollController()
    controller._update_metrics(max_extent=200.0, viewport_size=400, content_size=600)
    assert controller.max_extent == 200.0
    assert controller.viewport_size == 400
    assert controller.content_size == 600


def test_scroller_basic_creation():
    """Scroller should be created with a child widget."""
    child = Column([Text("Item 1"), Text("Item 2")])
    scroller = Scroller(child=child)
    assert scroller._child is child
    assert scroller._controller is not None
    assert scroller._owns_controller is True


def test_scroller_with_external_controller():
    """Scroller should accept external ScrollController."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scroller = Scroller(child=child, scroll_controller=controller)
    assert scroller._controller is controller
    assert scroller._owns_controller is False


def test_scroller_requires_child():
    """Scroller should raise ValueError if child is None."""
    with pytest.raises(ValueError, match="requires a child"):
        Scroller(child=None)


def test_scroller_preferred_size():
    """Scroller preferred_size should include padding."""
    child = Column([Text("Item")])
    scroller = Scroller(child=child, padding=10)
    child_w, child_h = child.preferred_size()
    scroller_w, scroller_h = scroller.preferred_size()
    assert scroller_w == child_w + 20
    assert scroller_h == child_h + 20


def test_scroller_direction():
    """Scroller should accept direction parameter."""
    child = Column([Text("Item")])
    scroller_v = Scroller(child=child, direction=ScrollDirection.VERTICAL)
    assert scroller_v.direction is ScrollDirection.VERTICAL
    scroller_h = Scroller(child=child, direction=ScrollDirection.HORIZONTAL)
    assert scroller_h.direction is ScrollDirection.HORIZONTAL


def test_scroller_defaults_to_axis_stretch_vertical():
    child = Column([Text("Item")])
    scroller = Scroller(child=child)
    assert scroller.height_sizing.kind == "flex"


def test_scroller_defaults_to_axis_stretch_horizontal():
    child = Row([Text("Item")])
    scroller = Scroller(child=child, direction=ScrollDirection.HORIZONTAL)
    assert scroller.width_sizing.kind == "flex"


def test_scroller_respects_explicit_sizing_override():
    child = Column([Text("Item")])
    scroller = Scroller(child=child, height=120)
    assert scroller.height_sizing.kind == "fixed"
    assert int(scroller.height_sizing.value) == 120


def test_scroller_updates_metrics_without_explicit_height():

    class TallWidget(Widget):

        def preferred_size(self):
            return (80, 400)

        def paint(self, canvas, x, y, w, h):
            del canvas, x, y, w, h

    scroller = Scroller(child=TallWidget())
    canvas = DummyCanvas()
    scroller.paint(canvas, 0, 0, 120, 150)
    axis_state = scroller._controller.axis_state(ScrollDirection.VERTICAL)
    assert axis_state.viewport_size.value == 150
    assert axis_state.content_size.value == 400
    assert axis_state.max_extent.value == 250


def test_scroller_updates_horizontal_metrics_without_explicit_width():

    class WideWidget(Widget):

        def preferred_size(self):
            return (360, 60)

        def paint(self, canvas, x, y, w, h):
            del canvas, x, y, w, h

    scroller = Scroller(child=WideWidget(), direction=ScrollDirection.HORIZONTAL)
    canvas = DummyCanvas()
    scroller.paint(canvas, 0, 0, 180, 80)
    axis_state = scroller._controller.axis_state(ScrollDirection.HORIZONTAL)
    assert axis_state.viewport_size.value == 180
    assert axis_state.content_size.value == 360
    assert axis_state.max_extent.value == 180


def test_scroller_rejects_controller_without_required_axis():
    child = Row([Text("Item")])
    controller = ScrollController()
    with pytest.raises(ValueError, match="required axis"):
        Scroller(child=child, direction=ScrollDirection.HORIZONTAL, scroll_controller=controller)


def test_scroller_scrollbar_config():
    """Scroller should accept scrollbar configuration."""
    child = Column([Text("Item")])
    behavior = ScrollbarBehavior(auto_hide=False)
    scroller = Scroller(child=child, scrollbar=behavior, scrollbar_padding=4, scrollbar_enabled=False)
    assert scroller.scrollbar_behavior is behavior
    assert scroller._scrollbar_enabled is False


def test_scroller_registers_children_in_store():
    """Child widget and scrollbar should be registered via ChildContainerMixin."""
    child = Column([Text("Item")])
    scroller = Scroller(child=child)
    viewport = next((c for c in scroller.children if isinstance(c, ScrollViewport)), None)
    assert viewport is not None
    assert child in viewport.children
    assert any((isinstance(c, Scrollbar) for c in scroller.children))


def test_scroller_scrollbar_disabled_removes_widget():
    """ScrollbarConfig.disabled should omit scrollbar child."""
    child = Column([Text("Item")])
    scroller = Scroller(child=child, scrollbar_enabled=False)
    viewport = next((c for c in scroller.children if isinstance(c, ScrollViewport)), None)
    assert viewport is not None
    assert child in viewport.children
    assert all((not isinstance(c, Scrollbar) for c in scroller.children))


def test_scroller_physics():
    """Scroller should accept physics parameter."""
    child = Column([Text("Item")])
    scroller_clamp = Scroller(child=child, physics=ScrollPhysics.CLAMP)
    assert scroller_clamp.physics is ScrollPhysics.CLAMP
    scroller_never = Scroller(child=child, physics=ScrollPhysics.NEVER)
    assert scroller_never.physics is ScrollPhysics.NEVER


def test_scroller_convenience_methods():
    """Scroller should provide convenience methods that delegate to controller."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scroller = Scroller(child=child, scroll_controller=controller)
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    scroller.scroll_to(50.0)
    assert controller.get_offset() == 50.0
    scroller.scroll_to_start()
    assert controller.get_offset() == 0.0
    scroller.scroll_to_end()
    assert controller.get_offset() == 100.0
    assert scroller.scroll_offset == 100.0
    assert scroller.max_scroll_extent == 100.0


def test_scroller_mount_unmount():
    """Scroller should subscribe/unsubscribe on mount/unmount."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scroller = Scroller(child=child, scroll_controller=controller)
    assert scroller._scroll_unsubscribe is None
    app = App(scroller, width=400, height=300)
    scroller.mount(app)
    assert scroller._scroll_unsubscribe is not None
    scroller.unmount()
    assert scroller._scroll_unsubscribe is None


def test_scroller_handle_scroll_event():
    """Scroller should handle mouse_scroll event."""
    controller = ScrollController()
    controller._update_metrics(max_extent=500.0, viewport_size=200, content_size=700)
    child = Column([Text(f"Item {i}") for i in range(50)])
    scroller = Scroller(child=child, scroll_controller=controller)
    handled = send_pointer_event_for_test(scroller, PointerEventType.SCROLL, 0, 0, scroll_y=3)
    assert handled is True
    assert controller.get_offset() == 60.0


def test_scroller_handle_scroll_event_physics_never():
    """Scroller with physics='never' should not handle scroll events."""
    controller = ScrollController()
    controller._update_metrics(max_extent=500.0, viewport_size=200, content_size=700)
    child = Column([Text("Item")])
    scroller = Scroller(child=child, scroll_controller=controller, physics=ScrollPhysics.NEVER)
    handled = send_pointer_event_for_test(scroller, PointerEventType.SCROLL, 0, 0, scroll_y=3)
    assert handled is False
    assert controller.get_offset() == 0.0


def test_scroller_offset_subscription():
    """Scroller should invalidate when offset changes."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scroller = Scroller(child=child, scroll_controller=controller)

    class MockApp:

        def __init__(self):
            self.invalidate_count = 0

        def invalidate(self):
            self.invalidate_count += 1

    app = MockApp()
    scroller._app = app
    scroller.on_mount()
    set_axis_offset(controller, 50.0)
    assert app.invalidate_count == 1
    set_axis_offset(controller, 100.0)
    assert app.invalidate_count == 2
    scroller.on_unmount()


def test_scroller_drag_updates_offset_via_mouse_move():
    controller = ScrollController()
    controller._update_metrics(max_extent=300.0, viewport_size=200, content_size=500)
    child = Column([Text(f"Item {i}") for i in range(10)])
    scroller = Scroller(child=child, scroll_controller=controller)
    scroller.set_last_rect(0, 0, 200, 200)
    assert send_pointer_event_for_test(scroller, PointerEventType.PRESS, 50, 150) is True
    assert send_pointer_event_for_test(scroller, PointerEventType.MOVE, 50, 100) is True
    assert controller.get_offset() > 0.0


def test_scroller_horizontal_drag_updates_offset_via_mouse_move():

    class WideWidget(Widget):

        def preferred_size(self):
            return (800, 100)

        def paint(self, canvas, x, y, w, h):
            pass

    controller = ScrollController(axes=(ScrollDirection.HORIZONTAL,), primary_axis=ScrollDirection.HORIZONTAL)
    controller._update_metrics(max_extent=500.0, viewport_size=300, content_size=800)
    scroller = Scroller(child=WideWidget(), direction=ScrollDirection.HORIZONTAL, scroll_controller=controller)
    scroller.set_last_rect(0, 0, 300, 150)
    assert send_pointer_event_for_test(scroller, PointerEventType.PRESS, 150, 50) is True
    assert send_pointer_event_for_test(scroller, PointerEventType.MOVE, 100, 50) is True
    assert controller.get_offset(axis=ScrollDirection.HORIZONTAL) > 0.0


def test_scroller_horizontal_scroll_wheel_direction():
    controller = ScrollController(axes=(ScrollDirection.HORIZONTAL,), primary_axis=ScrollDirection.HORIZONTAL)
    controller._update_metrics(max_extent=400.0, viewport_size=300, content_size=700)
    child = Row([Text(f"Item {i}") for i in range(10)], gap=8)
    scroller = Scroller(child=child, direction=ScrollDirection.HORIZONTAL, scroll_controller=controller)
    assert send_pointer_event_for_test(scroller, PointerEventType.SCROLL, 0, 0, scroll_x=-2) is True
    assert controller.get_offset(axis=ScrollDirection.HORIZONTAL) > 0.0
    prev = controller.get_offset(axis=ScrollDirection.HORIZONTAL)
    assert send_pointer_event_for_test(scroller, PointerEventType.SCROLL, 0, 0, scroll_x=2) is True
    assert controller.get_offset(axis=ScrollDirection.HORIZONTAL) < prev


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
