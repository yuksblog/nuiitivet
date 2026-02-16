"""Scrollbar widget: independent scrollbar drawing and event handling.

This is a minimal, reusable implementation that supports vertical scrollbars.
It derives colors from the current Theme (ColorRole.ON_SURFACE) and exposes
handle_event/draw APIs so containers (like Scroller) can delegate behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import time
from typing import Optional, Tuple

from nuiitivet.animation import Animatable, LinearMotion
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.widgeting.widget import Widget
from nuiitivet.colors.utils import hex_to_rgba
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import draw_round_rect, get_skia, make_paint, make_rect, rgba_to_skia_color  # noqa: F401
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.manager import manager as theme_manager
from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgets.interaction import (
    DraggableNode,
    InteractionHostMixin,
    InteractionState,
    PointerInputNode,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrollbarBehavior:
    """Immutable behavior configuration for :class:`Scrollbar`."""

    auto_hide: bool = True
    hide_delay: float = 1.0
    fade_duration: float = 0.15
    hide_threshold: float = 0.25
    track_click_behavior: str = "jump"
    interactive: bool = True
    hit_slop: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "hide_delay", max(0.0, float(self.hide_delay)))
        object.__setattr__(self, "fade_duration", max(0.0, float(self.fade_duration)))
        object.__setattr__(self, "hide_threshold", max(0.0, min(1.0, float(self.hide_threshold))))
        try:
            if self.track_click_behavior not in ("none", "page", "jump"):
                object.__setattr__(self, "track_click_behavior", "none")
        except Exception:
            exception_once(logger, "scrollbar_behavior_post_init_exc", "ScrollbarBehavior.__post_init__ failed")
            object.__setattr__(self, "track_click_behavior", "none")


class Scrollbar(InteractionHostMixin, Widget):
    """Minimal vertical scrollbar widget."""

    _offset_unsubscribe: Optional[object]
    _hide_timer: Optional[threading.Timer]
    _visibility_unsubscribe: Optional[object]

    def __init__(
        self,
        controller: ScrollController,
        behavior: Optional[ScrollbarBehavior] = None,
        *,
        direction: ScrollDirection | str = ScrollDirection.VERTICAL,
        thickness: int = 8,
        min_thumb_length: int = 24,
        padding: int | tuple | None = 0,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        super().__init__(width=width, height=height, padding=padding)
        beh = behavior or ScrollbarBehavior()
        self._controller = controller
        self._behavior = beh
        self.direction = direction if isinstance(direction, ScrollDirection) else ScrollDirection(direction)
        self.thickness = int(thickness)
        self.min_thumb_length = int(min_thumb_length)
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

    def _derive_colors(self, _unused=None):
        try:
            theme = theme_manager.current
            base = theme.get(ColorRole.ON_SURFACE)
        except Exception:
            base = "#000000"

        tr = hex_to_rgba(base, alpha=0.12)
        th = hex_to_rgba(base, alpha=0.70)

        track_color = rgba_to_skia_color(tr)
        thumb_color = rgba_to_skia_color(th)
        return track_color, thumb_color

    # --- drawing ---
    def draw_vertical(
        self,
        canvas,
        x: int,
        y: int,
        width: int,
        height: int,
        vp_x: int,
        vp_y: int,
        vp_w: int,
        vp_h: int,
    ):
        bar_x = x + width - self.thickness - self.padding[2]
        bar_y = vp_y
        bar_w = self.thickness
        bar_h = vp_h
        self.paint(canvas, bar_x, bar_y, bar_w, bar_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        content_extent = self._controller.axis_content_size(self.direction)
        viewport_extent = self._controller.axis_viewport_size(self.direction)
        if content_extent <= viewport_extent or viewport_extent <= 0:
            self.bar_rect = None
            self.thumb_rect = None
            return

        bar_x, bar_y, bar_w, bar_h = x, y, width, height

        try:
            theme = theme_manager.current
            from nuiitivet.material.theme.theme_data import MaterialThemeData

            mat = theme.extension(MaterialThemeData)
            roles = mat.roles if mat is not None else {}
            on_surface = roles.get(ColorRole.ON_SURFACE, "#000000")
            primary = roles.get(ColorRole.PRIMARY, "#000000")
        except Exception:
            on_surface = "#000000"
            primary = "#000000"

        tr = hex_to_rgba(on_surface, alpha=0.12)
        track_color = rgba_to_skia_color(tr)
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

        if self._pressed or self._dragging:
            thumb_base = primary
            thumb_alpha = 1.0
        elif self._thumb_hover:
            thumb_base = primary
            thumb_alpha = 0.9
        else:
            thumb_base = on_surface
            thumb_alpha = 0.7
        effective_alpha = thumb_alpha * vis_progress
        th = hex_to_rgba(thumb_base, alpha=effective_alpha)
        thumb_color = rgba_to_skia_color(th)
        tr_vis = hex_to_rgba(on_surface, alpha=0.12 * vis_progress)
        track_color = rgba_to_skia_color(tr_vis)
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


__all__ = ["Scrollbar", "ScrollbarBehavior"]
