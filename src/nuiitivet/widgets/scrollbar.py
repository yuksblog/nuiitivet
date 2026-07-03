"""Scrollbar widgets: independent scrollbar drawing and event handling.

Public API:

* :class:`VerticalScrollbar` — scrollbar for the vertical axis.
* :class:`HorizontalScrollbar` — scrollbar for the horizontal axis.

Both share :class:`_ScrollbarBase`, which holds the axis-parameterized drawing
and gesture logic. Per the size policy, only the **main axis** (scroll length)
is a public dimension; the **cross axis** is the fixed ``thickness``. Colors are
resolved at paint time from the generic theme seam via
:class:`~nuiitivet.scrolling.ScrollbarThemeData` (no direct Material dependency),
with per-instance overrides from :class:`~nuiitivet.scrolling.ScrollbarStyle`, and
the widgets expose paint / event APIs so containers (like ``*Scrollable``) can
delegate behavior.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import ClassVar, Optional, Tuple

from nuiitivet.animation import Animatable, LinearMotion
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.scrolling import ScrollbarBehavior, ScrollController, ScrollDirection, ScrollbarStyle, ScrollbarThemeData
from nuiitivet.widgeting.widget import Widget
from nuiitivet.colors.utils import apply_alpha_to_rgba
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import draw_round_rect, get_skia, make_paint, make_rect, rgba_to_skia_color  # noqa: F401
from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgets.interaction import (
    DraggableNode,
    InteractionHostMixin,
    InteractionState,
    PointerInputNode,
)

logger = logging.getLogger(__name__)


class _ScrollbarBase(InteractionHostMixin, Widget):
    """(Internal) Axis-parameterized scrollbar widget.

    Not part of the public API. Use :class:`VerticalScrollbar` or
    :class:`HorizontalScrollbar`, which fix the scroll axis via ``_direction``.

    Draws a track + thumb for a single scroll axis and delegates gestures
    (thumb drag, track click) to :class:`ScrollController`. Only the main-axis
    length is a public dimension; the cross axis is the fixed ``thickness``.
    """

    #: Scroll axis fixed by each concrete subclass.
    _direction: ClassVar[ScrollDirection]

    _offset_unsubscribe: Optional[object]
    _hide_timer: Optional[threading.Timer]
    _visibility_unsubscribe: Optional[object]

    def __init__(
        self,
        controller: ScrollController,
        behavior: Optional[ScrollbarBehavior] = None,
        *,
        length: SizingLike = None,
        style: Optional[ScrollbarStyle] = None,
    ) -> None:
        """Initialize shared scrollbar state.

        The bar knows only its own appearance; its placement (offset from the
        viewport edge) is decided by the enclosing container. See
        :class:`~nuiitivet.scrolling.ScrollableStyle`.

        Args:
            controller: The :class:`ScrollController` driving the scroll axis.
            behavior: Interaction behavior (auto-hide, track clicks…).
            length: Main-axis length sizing override (cross axis is
                ``thickness``). Maps to ``height`` for vertical scrollbars and
                ``width`` for horizontal scrollbars via the concrete subclass.
            style: Scrollbar appearance (geometry + optional per-instance color
                overrides). See :class:`~nuiitivet.scrolling.ScrollbarStyle`.
        """
        st = style or ScrollbarStyle()
        width, height = self._axis_sizing(length, st.thickness)
        super().__init__(width=width, height=height)
        beh = behavior or ScrollbarBehavior()
        self._controller = controller
        self._behavior = beh
        self._style = st
        self.direction = self._direction
        self.thickness = int(st.thickness)
        self.min_thumb_length = int(st.min_thumb_length)
        self.interactive = bool(beh.interactive)
        self.track_click_behavior = beh.track_click_behavior
        self.auto_hide = bool(beh.auto_hide)
        self.hide_delay = float(beh.hide_delay)
        self.fade_duration = float(beh.fade_duration)
        self.hide_threshold = float(beh.hide_threshold)
        self.bar_rect: Optional[Tuple[int, int, int, int]] = None
        self.thumb_rect: Optional[Tuple[int, int, int, int]] = None
        self._dragging = False
        self._drag_axis_start = 0.0
        self._active_pointer_id: Optional[int] = None
        self._bar_hover = False
        self._thumb_hover = False
        self._hovering = False
        self._pressed = False
        self._last_interaction = 0.0
        self._offset_unsubscribe = None
        self._hide_timer = None
        initial_visibility = 1.0
        motion = LinearMotion(duration=self.fade_duration) if self.fade_duration > 0.0 else None
        self._visibility = Animatable(initial_visibility, motion=motion)
        self._visibility_unsubscribe = None

        # Initialize InteractionHostMixin
        # We use DraggableNode for thumb interaction and PointerInputNode for track interaction.
        self._state = InteractionState(disabled=not self.interactive)

        # 1. Thumb Dragging
        self._thumb_node = DraggableNode(
            on_drag_start=self._on_thumb_drag_start,
            on_drag_update=self._on_thumb_drag_update,
            on_drag_end=self._on_thumb_drag_end,
            hit_test=self._hit_test_thumb,
        )
        self.add_node(self._thumb_node)

        # 1.5 Thumb Hover (since DraggableNode doesn't handle hover)
        self._thumb_hover_node = PointerInputNode(
            hit_test=self._hit_test_thumb,
        )
        self._thumb_hover_node.enable_hover(on_change=self._on_thumb_hover_change)
        self.add_node(self._thumb_hover_node)

        # 2. Track Clicking (Page/Jump)
        self._track_node = PointerInputNode(
            hit_test=self._hit_test_track,
        )
        self._track_node.enable_click(on_press=self._on_track_press)
        self._track_node.enable_hover(on_change=self._on_track_hover_change)
        self.add_node(self._track_node)

        # Note: We don't use the default self._pointer_node created by Mixin for main logic,
        # but it's there. We could remove it or just ignore it.
        # InteractionHostMixin creates self._pointer_node by default.
        # We can disable it or just let it be (it won't do much if we don't enable click/hover on it).

    # NOTE: hit_slop is provided by the behavior object.

    # Removed on_pointer_event override to use InteractionHostMixin logic
    # def on_pointer_event(self, event: PointerEvent) -> bool: ...

    def _on_interaction(self, skip_invalidate: bool = False) -> None:
        try:
            now = time.time()
            self._last_interaction = now
            try:
                if self._hide_timer is not None:
                    try:
                        self._hide_timer.cancel()
                    except Exception:
                        exception_once(logger, "scrollbar_hide_timer_cancel_exc", "Hide timer cancel raised")
                    self._hide_timer = None
            except Exception:
                exception_once(logger, "scrollbar_hide_timer_cleanup_exc", "Hide timer cleanup raised")

            if self.auto_hide:
                self._cancel_hide_timer()
                self._visibility.target = 1.0
                self._start_hide_fallback_timer()

            if not skip_invalidate:
                self.invalidate()
        except Exception:
            exception_once(logger, "scrollbar_on_interaction_exc", "Scrollbar on_interaction raised")

    # --- Node Callbacks ---

    def _hit_test_thumb(self, x: float, y: float) -> bool:
        return self._point_in_thumb(x, y, include_slop=True)

    def _hit_test_track(self, x: float, y: float) -> bool:
        # Track hit test should include the bar, but maybe exclude thumb if we want strict layering?
        # Usually, if thumb handles it, track doesn't need to.
        # But PointerInputNode iterates all nodes. If Thumb consumes it, Track won't see it?
        # InteractionHostMixin iterates all nodes.
        # DraggableNode returns True if it handles press.
        # So if Thumb handles press, Track won't get it.
        # However, for Hover, both might get it.
        return self._point_in_bar(x, y, include_slop=True)

    def _on_thumb_drag_start(self, event: PointerEvent) -> None:
        container = getattr(self, "_scroll_container", None)
        cancel = getattr(container, "cancel_content_drag", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                exception_once(logger, "scrollbar_cancel_content_drag_exc", "cancel_content_drag raised")
        self._dragging = True
        self._pressed = True
        self._active_pointer_id = event.id
        self._drag_axis_start = self._axis_value_from_pointer(event)
        self._on_interaction()

    def _on_thumb_drag_update(self, event: PointerEvent, dx: float, dy: float) -> None:
        current = self._axis_value_from_pointer(event)
        # Note: DraggableNode gives us dx, dy, but we calculate absolute position delta
        # based on start position to avoid accumulation errors, or we can use dx/dy.
        # The original logic used: delta = current - self._drag_axis_start
        # Let's stick to that logic using the event position.
        delta = current - self._drag_axis_start
        viewport_extent = self._controller.axis_viewport_size(self.direction)
        content_extent = self._controller.axis_content_size(self.direction)
        if viewport_extent > 0:
            scroll_delta = delta * (content_extent / viewport_extent)
            self._controller.scroll_by(scroll_delta, axis=self.direction)
            self._drag_axis_start = current
            self._on_interaction()

    def _on_thumb_drag_end(self, event: PointerEvent) -> None:
        self._dragging = False
        self._pressed = False
        self._active_pointer_id = None
        self._on_interaction()

    def _on_track_press(self, event: PointerEvent) -> None:
        container = getattr(self, "_scroll_container", None)
        cancel = getattr(container, "cancel_content_drag", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                exception_once(logger, "scrollbar_cancel_content_drag_exc", "cancel_content_drag raised")
        if not self.bar_rect:
            return

        behavior = getattr(self, "track_click_behavior", "none")
        if behavior not in ("page", "jump"):
            return

        if self.direction is ScrollDirection.VERTICAL:
            click_axis = event.y
            axis_origin = self.bar_rect[1]
            track_length = self.bar_rect[3]
            thumb_axis_start = self.thumb_rect[1] if self.thumb_rect else None
            thumb_length = self.thumb_rect[3] if self.thumb_rect else 0
        else:
            click_axis = event.x
            axis_origin = self.bar_rect[0]
            track_length = self.bar_rect[2]
            thumb_axis_start = self.thumb_rect[0] if self.thumb_rect else None
            thumb_length = self.thumb_rect[2] if self.thumb_rect else 0

        if behavior == "page":
            viewport = self._controller.axis_viewport_size(self.direction)
            if thumb_axis_start is None:
                return
            if click_axis < thumb_axis_start:
                self._controller.scroll_by(-viewport, axis=self.direction)
            elif click_axis > (thumb_axis_start + thumb_length):
                self._controller.scroll_by(viewport, axis=self.direction)
            self._on_interaction()
            return

        # Jump behavior
        if track_length <= 0:
            return
        max_offset = self._controller.axis_max_extent(self.direction)
        thumb_len = max(self.min_thumb_length, int((thumb_length) or (track_length * 0.1)))
        rel = float(click_axis - axis_origin) / float(max(1, track_length))
        rel = max(0.0, min(1.0, rel))
        thumb_pos = int((track_length - thumb_len) * rel)
        denom = max(1, track_length - thumb_len)
        scroll_ratio = float(thumb_pos) / float(denom) if denom > 0 else 0.0
        target_offset = scroll_ratio * max_offset
        self._controller.scroll_to(target_offset, axis=self.direction)
        self._on_interaction()

    def _on_track_hover_change(self, hovered: bool) -> None:
        self._bar_hover = hovered
        self._update_hover_visuals()

    def _on_thumb_hover_change(self, hovered: bool) -> None:
        self._thumb_hover = hovered
        self._update_hover_visuals()

    def _update_hover_visuals(self) -> None:
        try:
            self._hovering = self._bar_hover or self._thumb_hover
            self._on_interaction()
        except Exception:
            exception_once(logger, "scrollbar_update_hover_visuals_exc", "Scrollbar hover visuals update raised")

    def on_mount(self) -> None:
        try:
            if not self.auto_hide:
                self._last_interaction = time.time()

            def _visibility_cb(_value: float) -> None:
                try:
                    self.invalidate(immediate=True)
                except Exception:
                    exception_once(
                        logger, "scrollbar_visibility_invalidate_exc", "Scrollbar visibility invalidate raised"
                    )

            self._visibility_unsubscribe = self._visibility.subscribe(_visibility_cb)

            axis_state = self._controller.axis_state(self.direction)

            def _offset_cb(_value) -> None:
                try:
                    self._on_interaction()
                except Exception:
                    exception_once(logger, "scrollbar_offset_callback_exc", "Scrollbar offset callback raised")

            self._offset_unsubscribe = axis_state.offset.subscribe(_offset_cb)
        except Exception:
            exception_once(logger, "scrollbar_on_mount_exc", "Scrollbar on_mount raised")
            self._offset_unsubscribe = None
            self._visibility_unsubscribe = None

    def on_unmount(self) -> None:
        try:
            if self._offset_unsubscribe:
                try:
                    if hasattr(self._offset_unsubscribe, "dispose"):
                        try:
                            self._offset_unsubscribe.dispose()
                        except Exception:
                            exception_once(logger, "scrollbar_offset_dispose_exc", "Scrollbar offset dispose raised")
                finally:
                    self._offset_unsubscribe = None
        except Exception:
            exception_once(logger, "scrollbar_on_unmount_exc", "Scrollbar on_unmount raised")
        try:
            if self._visibility_unsubscribe:
                try:
                    if hasattr(self._visibility_unsubscribe, "dispose"):
                        self._visibility_unsubscribe.dispose()
                finally:
                    self._visibility_unsubscribe = None
        except Exception:
            exception_once(logger, "scrollbar_visibility_unsubscribe_exc", "Scrollbar visibility unsubscribe raised")

        try:
            self._visibility.stop()
        except Exception:
            exception_once(logger, "scrollbar_visibility_stop_exc", "Scrollbar visibility stop raised")

        self._cancel_hide_timer()

    def _on_hide_timer_thread(self) -> None:
        try:
            self._visibility.target = 0.0
            self.invalidate(immediate=True)
        except Exception:
            exception_once(
                logger, "scrollbar_hide_timer_visibility_exc", "Scrollbar hide timer visibility update raised"
            )
        try:
            timer = getattr(self, "_hide_timer", None)
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:
                    exception_once(logger, "scrollbar_hide_timer_cancel_exc", "Hide timer cancel raised")
                self._hide_timer = None
        except Exception:
            exception_once(logger, "scrollbar_hide_timer_cleanup_exc", "Hide timer cleanup raised")

    def _start_hide_fallback_timer(self) -> None:
        try:
            t = threading.Timer(self.hide_delay, self._on_hide_timer_thread)
            t.daemon = True
            t.start()
            self._hide_timer = t
        except Exception:
            exception_once(logger, "scrollbar_start_hide_timer_exc", "Scrollbar hide timer start raised")
            self._hide_timer = None

    def _cancel_hide_timer(self) -> None:
        timer = getattr(self, "_hide_timer", None)
        if timer is None:
            return
        try:
            timer.cancel()
        except Exception:
            exception_once(logger, "scrollbar_hide_timer_cancel_exc", "Hide timer cancel raised")
        self._hide_timer = None

    # --- drawing ---
    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        content_extent = self._controller.axis_content_size(self.direction)
        viewport_extent = self._controller.axis_viewport_size(self.direction)
        if content_extent <= viewport_extent or viewport_extent <= 0:
            self.bar_rect = None
            self.thumb_rect = None
            return

        bar_x, bar_y, bar_w, bar_h = x, y, width, height

        try:
            from nuiitivet.theme.theme import Theme

            theme: Optional[Theme] = Theme.of(self)
        except Exception:
            theme = None

        theme_data: Optional[ScrollbarThemeData] = None
        if theme is not None:
            try:
                theme_data = theme.extension(ScrollbarThemeData)
            except Exception:
                theme_data = None

        progress = 1.0 if not self.auto_hide else float(self._visibility.value)

        try:
            p = float(progress)
            vis_progress = 1.0 - (1.0 - p) ** 3
        except Exception:
            vis_progress = progress

        if vis_progress <= self.hide_threshold:
            self.bar_rect = (bar_x, bar_y, bar_w, bar_h)
            self.thumb_rect = None
            self.set_last_rect(bar_x, bar_y, bar_w, bar_h)
            return

        # Colors are resolved at paint time against the current theme so a single
        # palette renders correctly across light/dark modes; per-instance style
        # overrides win over the theme. Auto-hide visibility is applied as an
        # extra alpha multiplier on top.
        colors = self._style.resolve_colors(theme_data, theme)
        if self._pressed or self._dragging:
            thumb_rgba = colors["thumb_active"]
        elif self._thumb_hover:
            thumb_rgba = colors["thumb_hover"]
        else:
            thumb_rgba = colors["thumb"]

        thumb_color = rgba_to_skia_color(apply_alpha_to_rgba(thumb_rgba, vis_progress))
        track_color = rgba_to_skia_color(apply_alpha_to_rgba(colors["track"], vis_progress))
        track_paint = make_paint(color=track_color, style="fill", aa=True)
        corner_radius = (bar_w / 2) if self.direction is ScrollDirection.VERTICAL else (bar_h / 2)
        track_rect = make_rect(bar_x, bar_y, bar_w, bar_h)
        if track_rect is not None and track_paint is not None:
            draw_round_rect(canvas, track_rect, corner_radius, track_paint)

        track_length = bar_h if self.direction is ScrollDirection.VERTICAL else bar_w
        thumb_ratio = min(1.0, viewport_extent / content_extent)
        thumb_length = max(self.min_thumb_length, int(track_length * thumb_ratio))

        max_offset = self._controller.axis_max_extent(self.direction)
        current_offset = self._controller.get_offset(self.direction)
        scroll_ratio = current_offset / max_offset if max_offset > 0 else 0
        axis_origin = bar_y if self.direction is ScrollDirection.VERTICAL else bar_x
        thumb_axis = axis_origin + int((track_length - thumb_length) * scroll_ratio)

        thumb_paint = make_paint(color=thumb_color, style="fill", aa=True)
        if self.direction is ScrollDirection.VERTICAL:
            thumb_rect = make_rect(bar_x, thumb_axis, bar_w, thumb_length)
        else:
            thumb_rect = make_rect(thumb_axis, bar_y, thumb_length, bar_h)
        if thumb_rect is not None and thumb_paint is not None:
            draw_round_rect(canvas, thumb_rect, corner_radius, thumb_paint)

        self.bar_rect = (bar_x, bar_y, bar_w, bar_h)
        if self.direction is ScrollDirection.VERTICAL:
            self.thumb_rect = (bar_x, thumb_axis, bar_w, thumb_length)
        else:
            self.thumb_rect = (thumb_axis, bar_y, thumb_length, bar_h)
        self.set_last_rect(bar_x, bar_y, bar_w, bar_h)

    # Removed manual event handling methods (on_pointer_event, etc.)

    def _point_in_bar(self, x: float, y: float, *, include_slop: bool = True) -> bool:
        rect = self.bar_rect or self.last_rect
        if rect is None:
            return False
        bx, by, bw, bh = rect
        if include_slop:
            beh_hs = getattr(self._behavior, "hit_slop", None)
            hs = int(beh_hs) if beh_hs is not None else max(8, self.thickness)
            bx -= hs
            by -= hs
            bw += hs * 2
            bh += hs * 2
        return bx <= x <= bx + bw and by <= y <= by + bh

    def _point_in_thumb(self, x: float, y: float, *, include_slop: bool = False) -> bool:
        rect = self.thumb_rect
        if rect is None:
            return False
        tx, ty, tw, th = rect
        if include_slop:
            beh_hs = getattr(self._behavior, "hit_slop", None)
            hs = int(beh_hs) if beh_hs is not None else max(8, self.thickness)
            tx -= hs
            ty -= hs
            tw += hs * 2
            th += hs * 2
        return tx <= x <= tx + tw and ty <= y <= ty + th

    # Removed old manual event handling methods
    # _handle_pointer_event, _handle_pointer_press, _handle_pointer_release, _handle_pointer_cancel
    # _handle_thumb_drag, _handle_track_press, _start_thumb_drag, _stop_thumb_drag
    # _update_hover_states, _clear_hover_states

    def _axis_value_from_pointer(self, event: PointerEvent) -> float:
        if self.direction is ScrollDirection.VERTICAL:
            return float(event.y)
        return float(event.x)

    def cancel_drag(self) -> None:
        if not (self._dragging or self._pressed):
            return
        # Reset state manually since we don't have direct access to node's internal state reset
        # But DraggableNode handles cancel on pointer cancel event.
        # If we want to force cancel, we might need to expose a method on DraggableNode.
        # For now, just reset local flags.
        self._dragging = False
        self._pressed = False
        self._active_pointer_id = None
        self._on_interaction()

    @staticmethod
    def _axis_sizing(length: SizingLike, thickness: int) -> Tuple[SizingLike, SizingLike]:
        """Map the main-axis ``length`` onto ``(width, height)`` for the axis.

        The cross axis is fixed to ``thickness`` (not exposed publicly); the
        concrete subclass overrides this to assign ``length`` to the correct
        dimension. The base implementation raises to force a subclass.
        """
        raise NotImplementedError


class VerticalScrollbar(_ScrollbarBase):
    """Scrollbar for the vertical axis.

    Only ``length`` (mapped to ``height``) is a public dimension; the width is
    the fixed ``thickness`` (cross axis).
    """

    _direction = ScrollDirection.VERTICAL

    @staticmethod
    def _axis_sizing(length: SizingLike, thickness: int) -> Tuple[SizingLike, SizingLike]:
        return (int(thickness), length)


class HorizontalScrollbar(_ScrollbarBase):
    """Scrollbar for the horizontal axis.

    Only ``length`` (mapped to ``width``) is a public dimension; the height is
    the fixed ``thickness`` (cross axis).
    """

    _direction = ScrollDirection.HORIZONTAL

    @staticmethod
    def _axis_sizing(length: SizingLike, thickness: int) -> Tuple[SizingLike, SizingLike]:
        return (length, int(thickness))


__all__ = ["VerticalScrollbar", "HorizontalScrollbar"]
