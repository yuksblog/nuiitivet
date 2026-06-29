"""Scrollable: axis-specific containers that make a child scrollable.

Public API:

* :class:`VerticalScrollable` — scrolls its child along the vertical axis.
* :class:`HorizontalScrollable` — scrolls its child along the horizontal axis.

Both share :class:`_ScrollableBase`, which holds the direction-parameterized
layout / paint / gesture logic. The scroll *engine* configuration (``physics``
and ``scroll_multiplier``) lives on :class:`~nuiitivet.scrolling.ScrollController`;
scrollbar appearance is configured via
:class:`~nuiitivet.scrolling.ScrollbarStyle` and scrollbar
interaction via :class:`~nuiitivet.widgets.scrollbar.ScrollbarBehavior`.
"""

from __future__ import annotations

import logging
from typing import ClassVar, Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable.protocols import ReadOnlyObservableProtocol

from ..widgeting.widget import Widget
from ..scrolling import ScrollController, ScrollDirection, ScrollPhysics, ScrollbarStyle
from ..rendering.sizing import Sizing, SizingLike
from ..input.pointer import PointerEvent, PointerEventType
from ..widgets.scrollbar import Scrollbar, ScrollbarBehavior
from .scroll_viewport import ScrollViewport

logger = logging.getLogger(__name__)


ScrollbarVisibleLike = Union[bool, ReadOnlyObservableProtocol[bool]]


def _read_bool(value: ScrollbarVisibleLike) -> bool:
    if isinstance(value, ReadOnlyObservableProtocol):
        try:
            return bool(value.value)
        except Exception:
            exception_once(logger, "scrollable_read_visible_exc", "Failed to read scrollbar_visible observable")
            return True
    return bool(value)


class _ScrollableBase(Widget):
    """(Internal) Direction-parameterized scroll container.

    Not part of the public API. Use :class:`VerticalScrollable` or
    :class:`HorizontalScrollable`, which fix the scroll axis via ``_direction``.

    Makes a child widget scrollable if it exceeds the viewport. Supports mouse
    wheel, drag, and scrollbar interactions.
    """

    #: Scroll axis fixed by each concrete subclass.
    _direction: ClassVar[ScrollDirection]

    def __init__(
        self,
        child: Widget,
        *,
        controller: Optional[ScrollController] = None,
        scrollbar_visible: ScrollbarVisibleLike = True,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        behavior: Optional[ScrollbarBehavior] = None,
        style: Optional[ScrollbarStyle] = None,
    ) -> None:
        """Initialize the scrollable.

        Args:
            child: The widget to make scrollable.
            controller: External :class:`ScrollController` (auto-created when
                omitted). ``physics`` and ``scroll_multiplier`` are read from it.
            scrollbar_visible: Whether the scrollbar is shown. Accepts a ``bool``
                or an ``Observable[bool]`` for reactive visibility.
            width: Width sizing override.
            height: Height sizing override.
            padding: Inner padding of the viewport (scrolled area).
            behavior: Scrollbar interaction behavior (auto-hide, track clicks…).
            style: Scrollbar appearance (thickness, min thumb length, inset).
        """
        super().__init__(width=width, height=height)

        if child is None:
            raise ValueError("Scrollable requires a child widget")

        self._child = child
        self.direction = self._direction
        self._apply_axis_sizing_defaults()

        if controller is None:
            self._controller = ScrollController(axes=(self.direction,), primary_axis=self.direction)
            self._owns_controller = True
        else:
            if not controller.has_axis(self.direction):
                raise ValueError(f"ScrollController does not support required axis {self.direction}")
            self._controller = controller
            self._owns_controller = False

        # Scroll-engine configuration is owned by the controller.
        self.physics = self._controller.physics
        self.scroll_multiplier = self._controller.scroll_multiplier

        self._scrollbar_behavior = behavior or ScrollbarBehavior()
        self._scrollbar_style = style or ScrollbarStyle()
        self._scrollbar_visible: ScrollbarVisibleLike = scrollbar_visible

        self._viewport = ScrollViewport(
            child=child,
            controller=self._controller,
            direction=self.direction,
            padding=padding,
        )
        self.add_child(self._viewport)

        self._scrollbar = Scrollbar(
            self._controller,
            behavior=self._scrollbar_behavior,
            direction=self.direction,
            thickness=self._scrollbar_style.thickness,
            min_thumb_length=self._scrollbar_style.min_thumb_length,
            padding=self._scrollbar_style.inset,
        )
        self.add_child(self._scrollbar)

        # Allow the scrollbar to coordinate with this container (e.g. cancel an
        # active content drag when the user begins dragging the thumb).
        try:
            setattr(self._scrollbar, "_scroll_container", self)
        except Exception:
            exception_once(logger, "scrollable_set_scroll_container_exc", "Failed to set scrollbar._scroll_container")

        # Drag-scroll state
        self._is_dragging = False
        self._drag_start_pos = 0.0
        self._drag_start_offset = 0.0
        self._content_pointer_id: Optional[int] = None

        # Scrollbar regions (for hit-testing)
        self._scrollbar_rect: Optional[Tuple[int, int, int, int]] = None
        self._scrollbar_thumb_rect: Optional[Tuple[int, int, int, int]] = None

        # Listener disposal handle (may be a Disposable or a callable)
        self._scroll_unsubscribe: Optional[object] = None

    # --- Lifecycle ---

    def on_mount(self) -> None:
        """Listen for scroll changes on mount."""

        # Call App.invalidate() on scroll change (compatible with the tests' MockApp)
        def _offset_cb(_val):
            # Notify the app to redraw content positions
            try:
                if getattr(self, "_app", None) is not None:
                    self._app.invalidate()
            except Exception:
                exception_once(
                    logger,
                    "scrollable_offset_invalidate_exc",
                    "App.invalidate failed on scroll offset change",
                )

        axis_state = self._controller.axis_state(self.direction)
        self._scroll_unsubscribe = axis_state.offset.subscribe(_offset_cb)

        # Reactive scrollbar visibility: relayout / repaint when it changes.
        if isinstance(self._scrollbar_visible, ReadOnlyObservableProtocol):
            self.observe(self._scrollbar_visible, self._on_scrollbar_visible_changed)

    def _on_scrollbar_visible_changed(self, _value: bool) -> None:
        self.mark_needs_layout()
        self.invalidate()

    def on_unmount(self) -> None:
        """Dispose listeners on unmount."""
        if self._scroll_unsubscribe:
            try:
                # Expect a Disposable with dispose(); call it and clear.
                if hasattr(self._scroll_unsubscribe, "dispose"):
                    try:
                        self._scroll_unsubscribe.dispose()
                    except Exception:
                        exception_once(
                            logger,
                            "scrollable_scroll_unsubscribe_dispose_exc",
                            "Failed to dispose scroll subscription",
                        )
            finally:
                self._scroll_unsubscribe = None

    # --- Sizing ---

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Explicit sizes take priority, otherwise delegate to viewport"""
        # Get viewport's preferred size
        viewport_w, viewport_h = self._viewport.preferred_size(max_width=max_width, max_height=max_height)

        # Check if explicit sizes were provided
        w_sz = self.width_sizing
        h_sz = self.height_sizing

        # Apply explicit width if provided
        if w_sz.kind == "fixed":
            width = int(w_sz.value)
        else:
            width = viewport_w
            if max_width is not None:
                width = min(int(width), int(max_width))

        # Apply explicit height if provided
        if h_sz.kind == "fixed":
            height = int(h_sz.value)
        else:
            height = viewport_h
            if max_height is not None:
                height = min(int(height), int(max_height))

        return (width, height)

    def layout(self, width: int, height: int) -> None:
        if __debug__:
            # Keep consistent with WidgetKernel.layout()
            from ..runtime.threading import assert_ui_thread

            assert_ui_thread()

        self.clear_needs_layout()
        current = self.layout_rect
        x = int(current[0]) if current is not None else 0
        y = int(current[1]) if current is not None else 0
        self.set_layout_rect(x, y, width, height)

        viewport_width = int(width)
        viewport_height = int(height)

        wants_scrollbar = self._wants_scrollbar()
        reserve_always = bool(wants_scrollbar and (not bool(self._scrollbar_behavior.auto_hide)))

        if wants_scrollbar and reserve_always:
            if self.direction is ScrollDirection.VERTICAL:
                pad_r = self._scrollbar.padding[2]
                thickness = self._scrollbar.thickness
                viewport_width = max(0, viewport_width - thickness - pad_r)
            elif self.direction is ScrollDirection.HORIZONTAL:
                pad_b = self._scrollbar.padding[3]
                thickness = self._scrollbar.thickness
                viewport_height = max(0, viewport_height - thickness - pad_b)

        self._viewport.layout(viewport_width, viewport_height)
        self._viewport.set_layout_rect(0, 0, viewport_width, viewport_height)

        scrollbar = self._scrollbar

        if wants_scrollbar and self._should_show_scrollbar():
            if self.direction is ScrollDirection.VERTICAL:
                pad_r = scrollbar.padding[2]
                bar_x = int(width) - scrollbar.thickness - pad_r
                bar_y = 0
                bar_w = scrollbar.thickness
                bar_h = viewport_height
            else:
                pad_b = scrollbar.padding[3]
                bar_x = 0
                bar_y = int(height) - scrollbar.thickness - pad_b
                bar_w = viewport_width
                bar_h = scrollbar.thickness

            scrollbar.layout(bar_w, bar_h)
            scrollbar.set_layout_rect(bar_x, bar_y, bar_w, bar_h)
        else:
            # Ensure hit_test never targets the scrollbar when it is not visible.
            scrollbar.layout(0, 0)
            scrollbar.set_layout_rect(0, 0, 0, 0)

    # --- Painting ---

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """
        1. Measure the child's preferred size and record it on the controller.
        2. Clip to the viewport region.
        3. Apply the scroll offset and paint the child.
        4. Paint the scrollbar.
        """
        # Auto-layout fallback for tests or direct paint calls.
        try:
            if self._viewport.layout_rect is None:
                self.layout(width, height)
        except Exception:
            exception_once(logger, "scrollable_auto_layout_exc", "Auto layout failed in paint")

        # Record the painted rect (for hit-testing)
        self.set_last_rect(x, y, width, height)

        viewport_width = width
        viewport_height = height

        wants_scrollbar = self._wants_scrollbar()

        # Phase 1 behaviour:
        # - if scrollbar.auto_hide is True -> overlay: do NOT reserve space (draw on top)
        # - if scrollbar.auto_hide is False -> reserve-always: always reserve space for the scrollbar
        reserve_always = bool(wants_scrollbar and (not bool(self._scrollbar_behavior.auto_hide)))

        # If we must reserve space (auto_hide == False) subtract thickness regardless
        if wants_scrollbar and reserve_always:
            if self.direction is ScrollDirection.VERTICAL:
                pad_r = self._scrollbar.padding[2]
                viewport_width = max(0, viewport_width - self._scrollbar.thickness - pad_r)
            elif self.direction is ScrollDirection.HORIZONTAL:
                pad_b = self._scrollbar.padding[3]
                viewport_height = max(0, viewport_height - self._scrollbar.thickness - pad_b)

        self._viewport.paint(canvas, x, y, viewport_width, viewport_height)

        # Then: paint other children (e.g., scrollbar) on top
        if wants_scrollbar and self._should_show_scrollbar():
            viewport_rect = self._viewport.viewport_rect or (x, y, viewport_width, viewport_height)
            scrollbar = self._scrollbar
            if self.direction is ScrollDirection.VERTICAL:
                pad_r = scrollbar.padding[2]
                bar_x = x + width - scrollbar.thickness - pad_r
                bar_y = viewport_rect[1]
                bar_w = scrollbar.thickness
                bar_h = viewport_rect[3]
                try:
                    scrollbar.set_last_rect(bar_x, bar_y, bar_w, bar_h)
                    scrollbar.paint(canvas, bar_x, bar_y, bar_w, bar_h)
                    self._scrollbar_rect = getattr(scrollbar, "bar_rect", None)
                    self._scrollbar_thumb_rect = getattr(scrollbar, "thumb_rect", None)
                except Exception:
                    exception_once(logger, "scrollable_scrollbar_paint_exc", "Scrollbar paint failed")
            elif self.direction is ScrollDirection.HORIZONTAL:
                pad_b = scrollbar.padding[3]
                bar_x = viewport_rect[0]
                bar_y = y + height - scrollbar.thickness - pad_b
                bar_w = viewport_rect[2]
                bar_h = scrollbar.thickness
                try:
                    scrollbar.set_last_rect(bar_x, bar_y, bar_w, bar_h)
                    scrollbar.paint(canvas, bar_x, bar_y, bar_w, bar_h)
                    self._scrollbar_rect = getattr(scrollbar, "bar_rect", None)
                    self._scrollbar_thumb_rect = getattr(scrollbar, "thumb_rect", None)
                except Exception:
                    exception_once(logger, "scrollable_scrollbar_paint_h_exc", "Scrollbar paint failed (horizontal)")

    def _wants_scrollbar(self) -> bool:
        """Whether a scrollbar should participate in layout / paint at all."""
        return _read_bool(self._scrollbar_visible) and self.physics is not ScrollPhysics.NEVER

    def _should_show_scrollbar(self) -> bool:
        """Whether the scrollbar should currently be shown."""
        if self.physics is ScrollPhysics.NEVER:
            return False
        if not _read_bool(self._scrollbar_visible):
            return False
        return self._controller.axis_max_extent(self.direction) > 0

    def on_pointer_event(self, event: PointerEvent) -> bool:
        etype = event.type

        scrollbar = self._scrollbar
        dragging_id = getattr(scrollbar, "_active_pointer_id", None)
        if getattr(scrollbar, "_dragging", False) and dragging_id == event.id:
            # Fallback: when running without an App (no pointer capture manager),
            # ensure drag sequences still reach the scrollbar.
            try:
                return bool(scrollbar.dispatch_pointer_event(event))
            except Exception:
                exception_once(logger, "scrollable_scrollbar_dispatch_exc", "scrollbar.dispatch_pointer_event failed")
                return False

        if etype == PointerEventType.SCROLL:
            return self._handle_scroll(event)
        if etype == PointerEventType.PRESS:
            return self._start_content_drag(event)
        if etype == PointerEventType.MOVE:
            if self._is_dragging and event.id == self._content_pointer_id:
                return self._handle_drag(event)
            return False
        if etype == PointerEventType.HOVER:
            return False
        if etype == PointerEventType.RELEASE:
            if self._is_dragging and event.id == self._content_pointer_id:
                return self._finish_content_drag(cancel=False)
            return False
        if etype == PointerEventType.CANCEL:
            if self._content_pointer_id == event.id:
                return self._finish_content_drag(cancel=True)
            return False
        if etype in (PointerEventType.ENTER, PointerEventType.LEAVE):
            return False
        return False

    def _handle_scroll(self, event: PointerEvent) -> bool:
        if self.physics is ScrollPhysics.NEVER:
            return False

        if self.direction is ScrollDirection.VERTICAL:
            delta = event.scroll_y
        elif self.direction is ScrollDirection.HORIZONTAL:
            delta = event.scroll_x
            if abs(delta) < 1e-6:
                delta = event.scroll_y
        else:
            return False

        if abs(delta) < 0.01:
            return False
        self._controller.scroll_by(delta * self.scroll_multiplier, axis=self.direction)
        return True

    def _start_content_drag(self, event: PointerEvent) -> bool:
        if not self._point_in_viewport(event.x, event.y):
            return False
        scrollbar = self._scrollbar
        if getattr(scrollbar, "_dragging", False):
            try:
                scrollbar.cancel_drag()
            except Exception:
                exception_once(logger, "scrollable_scrollbar_cancel_drag_exc", "scrollbar.cancel_drag failed")
        self._is_dragging = True
        self._content_pointer_id = event.id
        self._drag_start_pos = self._pointer_axis_value(event)
        self._drag_start_offset = self._controller.get_offset(self.direction)
        try:
            self.capture_pointer(event)
        except Exception:
            exception_once(logger, "scrollable_capture_pointer_exc", "capture_pointer failed")
        return True

    def _handle_drag(self, event: PointerEvent) -> bool:
        axis_value = self._pointer_axis_value(event)
        delta = self._drag_start_pos - axis_value
        new_offset = self._drag_start_offset + delta
        self._controller.scroll_to(new_offset, axis=self.direction)
        return True

    def _finish_content_drag(self, *, cancel: bool) -> bool:
        if not self._is_dragging:
            return False
        pointer_id = self._content_pointer_id
        self._is_dragging = False
        self._content_pointer_id = None
        if pointer_id is not None:
            try:
                if cancel:
                    self.cancel_pointer(pointer_id)
                else:
                    self.release_pointer(pointer_id)
            except Exception:
                exception_once(logger, "scrollable_release_pointer_exc", "release/cancel pointer failed")
        return True

    def _cancel_content_drag(self) -> None:
        self._finish_content_drag(cancel=True)

    def cancel_content_drag(self) -> None:
        """Cancel an active content drag gesture (if any)."""

        self._finish_content_drag(cancel=True)

    def _point_in_viewport(self, x: float, y: float) -> bool:
        rect = getattr(self._viewport, "global_layout_rect", None)
        if rect is None:
            rect = getattr(self, "global_layout_rect", None)
        if rect is None:
            return False
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def _pointer_axis_value(self, event: PointerEvent) -> float:
        if self.direction is ScrollDirection.HORIZONTAL:
            return float(event.x)
        return float(event.y)

    # --- Convenience methods (also accessible via the widget) ---

    def scroll_to(self, offset: float) -> None:
        """Scroll to the given offset (delegates to the controller)."""
        self._controller.scroll_to(offset, axis=self.direction)

    def scroll_to_end(self) -> None:
        """Scroll to the end."""
        self._controller.scroll_to_end(axis=self.direction)

    def scroll_to_start(self) -> None:
        """Scroll to the start."""
        self._controller.scroll_to_start(axis=self.direction)

    @property
    def scroll_offset(self) -> float:
        """Current scroll offset."""
        return self._controller.get_offset(self.direction)

    @property
    def max_scroll_extent(self) -> float:
        """Maximum scroll extent."""
        return self._controller.axis_max_extent(self.direction)

    @property
    def scrollbar_behavior(self) -> ScrollbarBehavior:
        """Return the immutable scrollbar behavior configuration."""
        return self._scrollbar_behavior

    @property
    def scrollbar_style(self) -> ScrollbarStyle:
        """Return the immutable scrollbar visual style."""
        return self._scrollbar_style

    def _apply_axis_sizing_defaults(self) -> None:
        """Ensure the scroll axis stretches to parent constraints by default."""
        if self.direction is ScrollDirection.VERTICAL:
            if self.height_sizing.kind == "auto":
                self.height_sizing = Sizing.flex()
        elif self.direction is ScrollDirection.HORIZONTAL:
            if self.width_sizing.kind == "auto":
                self.width_sizing = Sizing.flex()


class VerticalScrollable(_ScrollableBase):
    """Scrolls its child along the vertical axis."""

    _direction = ScrollDirection.VERTICAL


class HorizontalScrollable(_ScrollableBase):
    """Scrolls its child along the horizontal axis."""

    _direction = ScrollDirection.HORIZONTAL


__all__ = ["VerticalScrollable", "HorizontalScrollable"]
