"""Scroller: 子widgetをスクロール可能にするレイアウトwidget"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once

from ..widgeting.widget import Widget
from ..scrolling import ScrollController, ScrollDirection, ScrollPhysics
from ..rendering.sizing import Sizing, SizingLike
from ..input.pointer import PointerEvent, PointerEventType
from ..widgets.scrollbar import Scrollbar, ScrollbarBehavior
from .scroll_viewport import ScrollViewport


logger = logging.getLogger(__name__)


class Scroller(Widget):
    """(Advanced) Low-level scroll container.

    Warning:
        This API is **provisional** and subject to change in future versions.
        Specifically, parameters related to scrollbars may be consolidated or moved.

    Note:
        Prefer using the `.scroll()` modifier. This widget is exposed for
        advanced customization.

    Makes a child widget scrollable if it exceeds the viewport.
    Supports mouse wheel and scrollbar interactions.
    """

    def __init__(
        self,
        child: Widget,
        *,
        scroll_controller: Optional[ScrollController] = None,
        direction: ScrollDirection | str = ScrollDirection.VERTICAL,
        physics: ScrollPhysics | str = ScrollPhysics.CLAMP,
        scrollbar: Optional[ScrollbarBehavior] = None,
        scrollbar_padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 2,
        scrollbar_enabled: bool = True,
        scrollbar_thickness: int | None = None,
        scrollbar_min_thumb_length: int | None = None,
        scroll_multiplier: float = 20.0,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        width: SizingLike = None,
        height: SizingLike = None,
    ):
        """Scroller を初期化

        Args:
            child: スクロール対象のwidget
            scroll_controller: 外部制御用のScrollController（省略時は自動生成）
            direction: スクロール方向（:class:`ScrollDirection`）
            physics: スクロール物理演算（:class:`ScrollPhysics`）
        scrollbar: スクロールバーの振る舞い設定（動作のみ）。レイアウト系は `scrollbar_padding` で指定します。
            scroll_multiplier: マウスホイール1ステップあたりのスクロール量（ピクセル）
            padding: viewport内側の余白
        """
        super().__init__(width=width, height=height)

        if child is None:
            raise ValueError("Scroller requires a child widget")

        self._child = child
        self.direction = direction if isinstance(direction, ScrollDirection) else ScrollDirection(direction)
        self._apply_axis_sizing_defaults()

        if scroll_controller is None:
            self._controller = ScrollController(axes=(self.direction,), primary_axis=self.direction)
            self._owns_controller = True
        else:
            if not scroll_controller.has_axis(self.direction):
                raise ValueError(f"ScrollController does not support required axis {self.direction}")
            self._controller = scroll_controller
            self._owns_controller = False
        self.physics = physics if isinstance(physics, ScrollPhysics) else ScrollPhysics(physics)
        self.scroll_multiplier = float(scroll_multiplier)

        # Behavior object (contains interaction/auto-hide settings)
        from ..widgets.scrollbar import ScrollbarBehavior as _SB

        self._scrollbar_behavior = scrollbar or _SB()
        self._scrollbar_enabled = bool(scrollbar_enabled)
        self._scrollbar_padding = scrollbar_padding

        self._viewport = ScrollViewport(
            child=child,
            controller=self._controller,
            direction=self.direction,
            padding=padding,
        )
        self.add_child(self._viewport)

        self._scrollbar: Optional[Scrollbar]
        if not self._scrollbar_enabled:
            self._scrollbar = None
        else:
            # resolve optional thickness/min_thumb overrides (fallback to Scrollbar defaults)
            thickness_val = int(scrollbar_thickness) if scrollbar_thickness is not None else None
            min_thumb_val = int(scrollbar_min_thumb_length) if scrollbar_min_thumb_length is not None else None
            # build kwargs conditionally to avoid passing None to Scrollbar
            # Pass explicit keyword arguments to keep mypy happy (avoid **dict with Any)
            if thickness_val is None and min_thumb_val is None:
                self._scrollbar = Scrollbar(
                    self._controller,
                    behavior=self._scrollbar_behavior,
                    direction=self.direction,
                    padding=self._scrollbar_padding,
                )
            else:
                self._scrollbar = Scrollbar(
                    self._controller,
                    behavior=self._scrollbar_behavior,
                    direction=self.direction,
                    thickness=thickness_val or 8,
                    min_thumb_length=min_thumb_val or 24,
                    padding=self._scrollbar_padding,
                )
            self.add_child(self._scrollbar)

            # Allow the scrollbar to coordinate with this container (e.g. cancel
            # an active content drag when the user begins dragging the thumb).
            try:
                setattr(self._scrollbar, "_scroll_container", self)
            except Exception:
                exception_once(logger, "scroller_set_scroll_container_exc", "Failed to set scrollbar._scroll_container")

        # ドラッグスクロール用の状態
        self._is_dragging = False
        self._drag_start_pos = 0.0
        self._drag_start_offset = 0.0
        self._content_pointer_id: Optional[int] = None

        # スクロールバーの領域（hit-test用）
        self._scrollbar_rect: Optional[Tuple[int, int, int, int]] = None
        self._scrollbar_thumb_rect: Optional[Tuple[int, int, int, int]] = None

        # リスナー解除用 (may be a Disposable or a callable)
        self._scroll_unsubscribe: Optional[object] = None

    # --- ライフサイクル ---

    def on_mount(self) -> None:
        """mount時にスクロール変更をリッスン"""

        # スクロール変更時は App.invalidate() を呼ぶ（tests の MockApp と互換）
        def _offset_cb(_val):
            # Notify the app to redraw content positions
            try:
                if getattr(self, "_app", None) is not None:
                    self._app.invalidate()
            except Exception:
                exception_once(
                    logger,
                    "scroller_offset_invalidate_exc",
                    "App.invalidate failed on scroll offset change",
                )

        axis_state = self._controller.axis_state(self.direction)
        self._scroll_unsubscribe = axis_state.offset.subscribe(_offset_cb)

    def on_unmount(self) -> None:
        """unmount時にリスナー解除"""
        if self._scroll_unsubscribe:
            try:
                # Expect a Disposable with dispose(); call it and clear.
                if hasattr(self._scroll_unsubscribe, "dispose"):
                    try:
                        self._scroll_unsubscribe.dispose()
                    except Exception:
                        exception_once(
                            logger,
                            "scroller_scroll_unsubscribe_dispose_exc",
                            "Failed to dispose scroll subscription",
                        )
            finally:
                self._scroll_unsubscribe = None

    # --- サイズ計算 ---

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

        wants_scrollbar = (self._scrollbar is not None) and self.physics is not ScrollPhysics.NEVER
        reserve_always = bool(wants_scrollbar and (not bool(self._scrollbar_behavior.auto_hide)))

        if wants_scrollbar and reserve_always:
            if self.direction is ScrollDirection.VERTICAL:
                pad_r = self._scrollbar.padding[2] if self._scrollbar is not None else 0
                thickness = self._scrollbar.thickness if self._scrollbar is not None else 0
                viewport_width = max(0, viewport_width - thickness - pad_r)
            elif self.direction is ScrollDirection.HORIZONTAL:
                pad_b = self._scrollbar.padding[3] if self._scrollbar is not None else 0
                thickness = self._scrollbar.thickness if self._scrollbar is not None else 0
                viewport_height = max(0, viewport_height - thickness - pad_b)

        self._viewport.layout(viewport_width, viewport_height)
        self._viewport.set_layout_rect(0, 0, viewport_width, viewport_height)

        scrollbar = self._scrollbar
        if scrollbar is None:
            return

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

    # --- 描画 ---

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """
        1. 子のpreferred_sizeを取得し、controllerに記録
        2. viewport領域をクリップ
        3. スクロールオフセットを適用して子を描画
        4. スクロールバーを描画
        """
        # Auto-layout fallback for tests or direct paint calls.
        try:
            if self._viewport.layout_rect is None:
                self.layout(width, height)
        except Exception:
            exception_once(logger, "scroller_auto_layout_exc", "Auto layout failed in paint")

        # 描画領域を記録（hit-test用）
        self.set_last_rect(x, y, width, height)

        viewport_width = width
        viewport_height = height

        wants_scrollbar = (self._scrollbar is not None) and self.physics is not ScrollPhysics.NEVER

        # Phase 1 behaviour:
        # - if scrollbar.auto_hide is True -> overlay: do NOT reserve space (draw on top)
        # - if scrollbar.auto_hide is False -> reserve-always: always reserve space for the scrollbar
        reserve_always = False
        if wants_scrollbar:
            reserve_always = not bool(self._scrollbar_behavior.auto_hide)

        # If we must reserve space (auto_hide == False) subtract thickness regardless
        if wants_scrollbar and reserve_always:
            if self.direction is ScrollDirection.VERTICAL:
                if self._scrollbar is not None:
                    pad_r = self._scrollbar.padding[2]
                    viewport_width = max(0, viewport_width - self._scrollbar.thickness - pad_r)
                else:
                    viewport_width = viewport_width
            elif self.direction is ScrollDirection.HORIZONTAL:
                if self._scrollbar is not None:
                    pad_b = self._scrollbar.padding[3]
                    viewport_height = max(0, viewport_height - self._scrollbar.thickness - pad_b)
                else:
                    viewport_height = viewport_height

        self._viewport.paint(canvas, x, y, viewport_width, viewport_height)

        # Then: paint other children (e.g., scrollbar) on top
        if wants_scrollbar and self._should_show_scrollbar():
            viewport_rect = self._viewport.viewport_rect or (x, y, viewport_width, viewport_height)
            if self.direction is ScrollDirection.VERTICAL:
                if self._scrollbar is not None:
                    pad_r = self._scrollbar.padding[2]
                    bar_x = x + width - self._scrollbar.thickness - pad_r
                    bar_y = viewport_rect[1]
                    bar_w = self._scrollbar.thickness
                    bar_h = viewport_rect[3]
                else:
                    bar_x = x + width
                    bar_y = viewport_rect[1]
                    bar_w = 0
                    bar_h = viewport_rect[3]

                # set scrollbar last_rect so hit-testing works via Widget.hit_test
                scrollbar = self._scrollbar
                if scrollbar is not None:
                    try:
                        scrollbar.set_last_rect(bar_x, bar_y, bar_w, bar_h)
                        # also forward paint to the child via its paint API
                        scrollbar.paint(canvas, bar_x, bar_y, bar_w, bar_h)
                        # record rects for backward-compat / tests
                        self._scrollbar_rect = getattr(scrollbar, "bar_rect", None)
                        self._scrollbar_thumb_rect = getattr(scrollbar, "thumb_rect", None)
                    except Exception:
                        exception_once(logger, "scroller_scrollbar_paint_exc", "Scrollbar paint failed")
            elif self.direction is ScrollDirection.HORIZONTAL:
                if self._scrollbar is not None:
                    pad_b = self._scrollbar.padding[3]
                    bar_x = viewport_rect[0]
                    bar_y = y + height - self._scrollbar.thickness - pad_b
                    bar_w = viewport_rect[2]
                    bar_h = self._scrollbar.thickness
                else:
                    bar_x = viewport_rect[0]
                    bar_y = y + height
                    bar_w = viewport_rect[2]
                    bar_h = 0

                scrollbar = self._scrollbar
                if scrollbar is not None:
                    try:
                        scrollbar.set_last_rect(bar_x, bar_y, bar_w, bar_h)
                        scrollbar.paint(canvas, bar_x, bar_y, bar_w, bar_h)
                        self._scrollbar_rect = getattr(scrollbar, "bar_rect", None)
                        self._scrollbar_thumb_rect = getattr(scrollbar, "thumb_rect", None)
                    except Exception:
                        exception_once(logger, "scroller_scrollbar_paint_h_exc", "Scrollbar paint failed (horizontal)")

    def _should_show_scrollbar(self) -> bool:
        """スクロールバーを表示すべきか判定（確定版）"""
        if self.physics is ScrollPhysics.NEVER:
            return False
        return self._controller.axis_max_extent(self.direction) > 0

    def on_pointer_event(self, event: PointerEvent) -> bool:
        etype = event.type

        scrollbar = self._scrollbar
        if scrollbar is not None:
            dragging_id = getattr(scrollbar, "_active_pointer_id", None)
            if getattr(scrollbar, "_dragging", False) and dragging_id == event.id:
                # Fallback: when running without an App (no pointer capture manager),
                # ensure drag sequences still reach the scrollbar.
                try:
                    return bool(scrollbar.dispatch_pointer_event(event))
                except Exception:
                    exception_once(logger, "scroller_scrollbar_dispatch_exc", "scrollbar.dispatch_pointer_event failed")
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
                delta = -event.scroll_y
            else:
                delta = -delta
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
        if scrollbar is not None and getattr(scrollbar, "_dragging", False):
            try:
                scrollbar.cancel_drag()
            except Exception:
                exception_once(logger, "scroller_scrollbar_cancel_drag_exc", "scrollbar.cancel_drag failed")
        self._is_dragging = True
        self._content_pointer_id = event.id
        self._drag_start_pos = self._pointer_axis_value(event)
        self._drag_start_offset = self._controller.get_offset(self.direction)
        try:
            self.capture_pointer(event)
        except Exception:
            exception_once(logger, "scroller_capture_pointer_exc", "capture_pointer failed")
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
                exception_once(logger, "scroller_release_pointer_exc", "release/cancel pointer failed")
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

    # --- 便利メソッド（widget経由でもアクセス可能） ---

    def scroll_to(self, offset: float) -> None:
        """指定位置にスクロール（内部Controllerに委譲）"""
        self._controller.scroll_to(offset, axis=self.direction)

    def scroll_to_end(self) -> None:
        """末尾にスクロール"""
        self._controller.scroll_to_end(axis=self.direction)

    def scroll_to_start(self) -> None:
        """先頭にスクロール"""
        self._controller.scroll_to_start(axis=self.direction)

    @property
    def scroll_offset(self) -> float:
        """現在のスクロール位置"""
        return self._controller.get_offset(self.direction)

    @property
    def max_scroll_extent(self) -> float:
        """最大スクロール距離"""
        return self._controller.axis_max_extent(self.direction)

    @property
    def scrollbar_behavior(self) -> ScrollbarBehavior:
        """Return the immutable scrollbar behavior configuration."""
        return self._scrollbar_behavior

    def _apply_axis_sizing_defaults(self) -> None:
        """Ensure the scroll axis stretches to parent constraints by default."""
        if self.direction is ScrollDirection.VERTICAL:
            if self.height_sizing.kind == "auto":
                self.height_sizing = Sizing.flex()
        elif self.direction is ScrollDirection.HORIZONTAL:
            if self.width_sizing.kind == "auto":
                self.width_sizing = Sizing.flex()
