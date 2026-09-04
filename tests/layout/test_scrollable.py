"""Tests for VerticalScrollable / HorizontalScrollable and ScrollController."""

import pytest
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.scrolling import ScrollController, ScrollDirection, ScrollPhysics
from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.scrollable import VerticalScrollable, HorizontalScrollable
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.scrolling import ScrollableStyle, ScrollbarBehavior, ScrollbarStyle
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.scrollbar import _ScrollbarBase
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


def test_scroll_controller_physics_and_multiplier_defaults():
    """ScrollController should own physics / scroll_multiplier with sane defaults."""
    controller = ScrollController()
    assert controller.physics is ScrollPhysics.CLAMP
    assert controller.scroll_multiplier == 20.0


def test_scroll_controller_physics_and_multiplier_overrides():
    controller = ScrollController(physics="never", scroll_multiplier=30.0)
    assert controller.physics is ScrollPhysics.NEVER
    assert controller.scroll_multiplier == 30.0


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


def test_scrollable_basic_creation():
    """VerticalScrollable should be created with a child widget."""
    child = Column([Text("Item 1"), Text("Item 2")])
    scrollable = VerticalScrollable(child=child)
    assert scrollable._child is child
    assert scrollable._controller is not None
    assert scrollable._owns_controller is True
    assert scrollable.direction is ScrollDirection.VERTICAL


def test_scrollable_with_external_controller():
    """VerticalScrollable should accept external ScrollController."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, controller=controller)
    assert scrollable._controller is controller
    assert scrollable._owns_controller is False


def test_scrollable_requires_child():
    """Scrollable should raise ValueError if child is None."""
    with pytest.raises(ValueError, match="requires a child"):
        VerticalScrollable(child=None)


def test_scrollable_preferred_size():
    """Scrollable preferred_size should include padding."""
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, style=ScrollableStyle(viewport_padding=10))
    child_w, child_h = child.preferred_size()
    scrollable_w, scrollable_h = scrollable.preferred_size()
    assert scrollable_w == child_w + 20
    assert scrollable_h == child_h + 20


def test_scrollable_axis_is_fixed_by_class():
    """Axis is encoded in the concrete class, not a parameter."""
    assert VerticalScrollable(child=Column([Text("Item")])).direction is ScrollDirection.VERTICAL
    assert HorizontalScrollable(child=Row([Text("Item")])).direction is ScrollDirection.HORIZONTAL


def test_scrollable_defaults_to_axis_stretch_vertical():
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child)
    assert scrollable.height_sizing.kind == "weight"


def test_scrollable_defaults_to_axis_stretch_horizontal():
    child = Row([Text("Item")])
    scrollable = HorizontalScrollable(child=child)
    assert scrollable.width_sizing.kind == "weight"


def test_scrollable_respects_explicit_sizing_override():
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, height=120)
    assert scrollable.height_sizing.kind == "fixed"
    assert int(scrollable.height_sizing.value) == 120


def test_scrollable_updates_metrics_without_explicit_height():

    class TallWidget(Widget):

        def preferred_size(self):
            return (80, 400)

        def paint(self, canvas, x, y, w, h):
            del canvas, x, y, w, h

    scrollable = VerticalScrollable(child=TallWidget())
    canvas = DummyCanvas()
    scrollable.paint(canvas, 0, 0, 120, 150)
    axis_state = scrollable._controller.axis_state(ScrollDirection.VERTICAL)
    assert axis_state.viewport_size.value == 150
    assert axis_state.content_size.value == 400
    assert axis_state.max_extent.value == 250


def test_scrollable_updates_horizontal_metrics_without_explicit_width():

    class WideWidget(Widget):

        def preferred_size(self):
            return (360, 60)

        def paint(self, canvas, x, y, w, h):
            del canvas, x, y, w, h

    scrollable = HorizontalScrollable(child=WideWidget())
    canvas = DummyCanvas()
    scrollable.paint(canvas, 0, 0, 180, 80)
    axis_state = scrollable._controller.axis_state(ScrollDirection.HORIZONTAL)
    assert axis_state.viewport_size.value == 180
    assert axis_state.content_size.value == 360
    assert axis_state.max_extent.value == 180


def test_scrollable_rejects_controller_without_required_axis():
    child = Row([Text("Item")])
    controller = ScrollController()  # vertical-only
    with pytest.raises(ValueError, match="required axis"):
        HorizontalScrollable(child=child, controller=controller)


def test_scrollable_accepts_behavior_and_styles():
    """Scrollable should accept behavior + appearance + placement config objects."""
    child = Column([Text("Item")])
    behavior = ScrollbarBehavior(auto_hide=False)
    scrollbar_style = ScrollbarStyle(thickness=12)
    style = ScrollableStyle(scrollbar_padding=4)
    scrollable = VerticalScrollable(
        child=child, scrollbar_behavior=behavior, scrollbar_style=scrollbar_style, style=style
    )
    assert scrollable.scrollbar_behavior is behavior
    assert scrollable.scrollbar_style is scrollbar_style
    assert scrollable.scrollable_style is style
    assert scrollable._scrollbar.thickness == 12
    assert scrollable._scrollbar_padding[2] == 4


def test_scrollable_registers_children_in_store():
    """Child widget and scrollbar should be registered via ChildContainerMixin."""
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child)
    viewport = next((c for c in scrollable.children if isinstance(c, ScrollViewport)), None)
    assert viewport is not None
    assert child in viewport.children
    assert any((isinstance(c, _ScrollbarBase) for c in scrollable.children))


def test_scrollable_scrollbar_visible_false_suppresses_display():
    """scrollbar_visible=False keeps the scrollbar from participating in layout/paint."""
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, scrollbar_visible=False)
    # The scrollbar widget is still mounted as a child...
    assert any((isinstance(c, _ScrollbarBase) for c in scrollable.children))
    # ...but it never wants to show.
    assert scrollable._wants_scrollbar() is False
    assert scrollable._should_show_scrollbar() is False


def test_scrollable_physics_from_controller():
    """Scrollable.physics is sourced from its controller."""
    child = Column([Text("Item")])
    clamp = VerticalScrollable(child=child, controller=ScrollController(physics="clamp"))
    assert clamp.physics is ScrollPhysics.CLAMP
    never = VerticalScrollable(child=child, controller=ScrollController(physics="never"))
    assert never.physics is ScrollPhysics.NEVER


def test_scrollable_convenience_methods():
    """Scrollable should provide convenience methods that delegate to controller."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, controller=controller)
    controller._update_metrics(max_extent=100.0, viewport_size=200, content_size=300)
    scrollable.scroll_to(50.0)
    assert controller.get_offset() == 50.0
    scrollable.scroll_to_start()
    assert controller.get_offset() == 0.0
    scrollable.scroll_to_end()
    assert controller.get_offset() == 100.0
    assert scrollable.scroll_offset == 100.0
    assert scrollable.max_scroll_extent == 100.0


def test_scrollable_mount_unmount():
    """Scrollable should subscribe/unsubscribe on mount/unmount."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, controller=controller)
    assert scrollable._scroll_unsubscribe is None
    app = App(Window(content=scrollable, width=400, height=300))
    scrollable.mount(app)
    assert scrollable._scroll_unsubscribe is not None
    scrollable.unmount()
    assert scrollable._scroll_unsubscribe is None


def test_scrollable_handle_scroll_event():
    """Scrollable should handle mouse_scroll event."""
    controller = ScrollController()
    controller._update_metrics(max_extent=500.0, viewport_size=200, content_size=700)
    child = Column([Text(f"Item {i}") for i in range(50)])
    scrollable = VerticalScrollable(child=child, controller=controller)
    handled = send_pointer_event_for_test(scrollable, PointerEventType.SCROLL, 0, 0, scroll_y=3)
    assert handled is True
    assert controller.get_offset() == 60.0


def test_scrollable_handle_scroll_event_physics_never():
    """Scrollable with physics='never' should not handle scroll events."""
    controller = ScrollController(physics="never")
    controller._update_metrics(max_extent=500.0, viewport_size=200, content_size=700)
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, controller=controller)
    handled = send_pointer_event_for_test(scrollable, PointerEventType.SCROLL, 0, 0, scroll_y=3)
    assert handled is False
    assert controller.get_offset() == 0.0


def test_scrollable_offset_subscription():
    """Scrollable should invalidate when offset changes."""
    controller = ScrollController()
    child = Column([Text("Item")])
    scrollable = VerticalScrollable(child=child, controller=controller)

    class MockApp:

        def __init__(self):
            self.invalidate_count = 0

        def invalidate(self):
            self.invalidate_count += 1

    app = MockApp()
    scrollable._app = app
    scrollable.on_mount()
    set_axis_offset(controller, 50.0)
    assert app.invalidate_count == 1
    set_axis_offset(controller, 100.0)
    assert app.invalidate_count == 2
    scrollable.on_unmount()


def test_scrollable_drag_updates_offset_via_mouse_move():
    controller = ScrollController()
    controller._update_metrics(max_extent=300.0, viewport_size=200, content_size=500)
    child = Column([Text(f"Item {i}") for i in range(10)])
    scrollable = VerticalScrollable(child=child, controller=controller)
    scrollable.set_last_rect(0, 0, 200, 200)
    assert send_pointer_event_for_test(scrollable, PointerEventType.PRESS, 50, 150) is True
    assert send_pointer_event_for_test(scrollable, PointerEventType.MOVE, 50, 100) is True
    assert controller.get_offset() > 0.0


def test_scrollable_horizontal_drag_updates_offset_via_mouse_move():

    class WideWidget(Widget):

        def preferred_size(self):
            return (800, 100)

        def paint(self, canvas, x, y, w, h):
            pass

    controller = ScrollController(axes=(ScrollDirection.HORIZONTAL,), primary_axis=ScrollDirection.HORIZONTAL)
    controller._update_metrics(max_extent=500.0, viewport_size=300, content_size=800)
    scrollable = HorizontalScrollable(child=WideWidget(), controller=controller)
    scrollable.set_last_rect(0, 0, 300, 150)
    assert send_pointer_event_for_test(scrollable, PointerEventType.PRESS, 150, 50) is True
    assert send_pointer_event_for_test(scrollable, PointerEventType.MOVE, 100, 50) is True
    assert controller.get_offset(axis=ScrollDirection.HORIZONTAL) > 0.0


def test_scrollable_horizontal_scroll_wheel_direction():
    controller = ScrollController(axes=(ScrollDirection.HORIZONTAL,), primary_axis=ScrollDirection.HORIZONTAL)
    controller._update_metrics(max_extent=400.0, viewport_size=300, content_size=700)
    child = Row([Text(f"Item {i}") for i in range(10)], gap=8)
    scrollable = HorizontalScrollable(child=child, controller=controller)
    assert send_pointer_event_for_test(scrollable, PointerEventType.SCROLL, 0, 0, scroll_x=2) is True
    assert controller.get_offset(axis=ScrollDirection.HORIZONTAL) > 0.0
    prev = controller.get_offset(axis=ScrollDirection.HORIZONTAL)
    assert send_pointer_event_for_test(scrollable, PointerEventType.SCROLL, 0, 0, scroll_x=-2) is True
    assert controller.get_offset(axis=ScrollDirection.HORIZONTAL) < prev


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


def test_vertical_scrollable_gives_weight_content_the_viewport_width():
    """A weight has no intrinsic size, so the viewport must supply it.

    Measured alone, ``width="wt"`` answers with padding only. Laying the content
    out at that answer is what shrink-wraps a full-width card inside a list.
    """
    child = Column([Text("Item")], width="wt")
    scrollable = VerticalScrollable(child=child)

    scrollable.layout(300, 200)

    assert child.layout_rect is not None
    assert int(child.layout_rect[2]) == 300


def test_horizontal_scrollable_gives_weight_content_the_viewport_height():
    child = Row([Text("Item")], height="wt")
    scrollable = HorizontalScrollable(child=child)

    scrollable.layout(300, 200)

    assert child.layout_rect is not None
    assert int(child.layout_rect[3]) == 200


def test_scrollable_leaves_the_scroll_axis_content_driven():
    """The cross axis is substituted; the scroll axis never is.

    Content taller than the viewport must stay tall, or there is nothing to
    scroll.
    """
    child = Column([Text("Item") for _ in range(40)], width="wt")
    scrollable = VerticalScrollable(child=child)

    scrollable.layout(300, 100)

    assert child.layout_rect is not None
    assert int(child.layout_rect[3]) > 100


def test_scrollable_does_not_stretch_auto_sized_content():
    """``auto`` keeps its preferred size, and may still overflow the cross axis."""
    child = Column([Text("Item")], width=500)
    scrollable = VerticalScrollable(child=child)

    scrollable.layout(300, 200)

    assert child.layout_rect is not None
    assert int(child.layout_rect[2]) == 500


def test_reactive_scrollbar_visibility_binding_is_disposed_on_unmount():
    """A re-mounted Scrollable must not accumulate visibility subscriptions.

    ``on_mount`` registers the ``scrollbar_visible`` observer through
    ``observe()``, and only ``BindingHostMixin.on_unmount`` disposes it -- so
    an ``on_unmount`` that skipped ``super()`` left one live subscription per
    mount, each firing a relayout against a detached widget.
    """
    from nuiitivet.observable import Observable

    class _CountingApp:
        def invalidate(self, immediate: bool = False) -> None:
            del immediate

    visible = Observable(True)
    scrollable = VerticalScrollable(child=Column([Text("Item")]), scrollbar_visible=visible)
    app = _CountingApp()

    for _ in range(3):
        scrollable.mount(app)
        scrollable.unmount()

    relayouts = []
    scrollable.mark_needs_layout = lambda: relayouts.append(1)
    visible.value = False

    assert relayouts == []
