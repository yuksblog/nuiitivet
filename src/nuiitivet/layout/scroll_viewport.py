"""ScrollViewport: clipped scrolling surface for Scroller and related widgets."""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.widget import Widget
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.layout.metrics import normalize_padding
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import clip_rect, make_rect


_logger = logging.getLogger(__name__)


class ScrollViewport(Widget):
    """Applies scroll offset and clipping to a single child widget."""

    def __init__(
        self,
        child: Widget,
        controller: ScrollController,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        direction: ScrollDirection = ScrollDirection.VERTICAL,
    ) -> None:
        """Initialize the ScrollViewport.

        Args:
            child: The scrollable content widget.
            controller: The ScrollController managing offset and events.
            width: Viewport width.
            height: Viewport height.
            padding: Padding applied *inside* the viewport (scrolled area).
            direction: The axis along which scrolling is permitted.
        """
        super().__init__(width=width, height=height)
        if child is None:
            raise ValueError("ScrollViewport requires a child widget")
        self._content = child
        self.add_child(child)
        self._controller = controller
        self.direction = direction
        self._pad = normalize_padding(padding)
        self._viewport_rect: Optional[Tuple[int, int, int, int]] = None

    @property
    def content(self) -> Widget:
        return self._content

    @property
    def viewport_rect(self) -> Optional[Tuple[int, int, int, int]]:
        return self._viewport_rect

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        inner_max_w: Optional[int] = None
        inner_max_h: Optional[int] = None
        if max_width is not None:
            inner_max_w = max(0, int(max_width) - int(self._pad[0]) - int(self._pad[2]))
        if max_height is not None:
            inner_max_h = max(0, int(max_height) - int(self._pad[1]) - int(self._pad[3]))

        # Don't constrain in scroll direction
        if self.direction == ScrollDirection.VERTICAL:
            cw, ch = measure_preferred_size(self._content, max_width=inner_max_w, max_height=None)
        elif self.direction == ScrollDirection.HORIZONTAL:
            cw, ch = measure_preferred_size(self._content, max_width=None, max_height=inner_max_h)
        else:
            cw, ch = measure_preferred_size(self._content, max_width=inner_max_w, max_height=inner_max_h)

        default_w = cw + self._pad[0] + self._pad[2]
        default_h = ch + self._pad[1] + self._pad[3]

        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        elif w_dim.kind == "flex":
            width = self._pad[0] + self._pad[2]
        else:
            width = default_w

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        elif h_dim.kind == "flex":
            height = self._pad[1] + self._pad[3]
        else:
            height = default_h

        if max_width is not None and w_dim.kind != "fixed":
            width = min(int(width), int(max_width))
        if max_height is not None and h_dim.kind != "fixed":
            height = min(int(height), int(max_height))

        return (width, height)

    def requires_scrollbar(self, width: int, height: int) -> bool:
        inner_width = max(0, width - self._pad[0] - self._pad[2])
        inner_height = max(0, height - self._pad[1] - self._pad[3])
        if self.direction is ScrollDirection.VERTICAL:
            cw, ch = measure_preferred_size(self._content, max_width=inner_width)
        elif self.direction is ScrollDirection.HORIZONTAL:
            cw, ch = measure_preferred_size(self._content, max_height=inner_height)
        else:
            cw, ch = measure_preferred_size(self._content, max_width=inner_width, max_height=inner_height)
        if self.direction is ScrollDirection.VERTICAL:
            return ch > inner_height
        if self.direction is ScrollDirection.HORIZONTAL:
            return cw > inner_width
        return False

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        content = self._content
        if content is None:
            return

        pad_l, pad_t, pad_r, pad_b = self._pad
        vp_w = max(0, width - pad_l - pad_r)
        vp_h = max(0, height - pad_t - pad_b)

        # Store viewport size for paint/hit_test
        self._vp_size = (vp_w, vp_h)

        if self.direction is ScrollDirection.VERTICAL:
            content_w, content_h = measure_preferred_size(content, max_width=vp_w)
        elif self.direction is ScrollDirection.HORIZONTAL:
            content_w, content_h = measure_preferred_size(content, max_height=vp_h)
        else:
            content_w, content_h = measure_preferred_size(content, max_width=vp_w, max_height=vp_h)

        # Update metrics during layout phase
        self._update_scroll_metrics(content_w, content_h, vp_w, vp_h)

        # Layout content with its preferred size
        # Note: We layout content at (pad_l, pad_t) relative to viewport origin.
        # Scroll offset is applied during paint.
        content.layout(content_w, content_h)
        content.set_layout_rect(pad_l, pad_t, content_w, content_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        content = self._content
        if content is None:
            return

        pad_l, pad_t, pad_r, pad_b = self._pad

        # Reconstruct viewport rect in absolute coordinates
        vp_x = x + pad_l
        vp_y = y + pad_t

        # Use cached viewport size from layout if available, else fallback
        if hasattr(self, "_vp_size"):
            vp_w, vp_h = self._vp_size
        else:
            vp_w = max(0, width - pad_l - pad_r)
            vp_h = max(0, height - pad_t - pad_b)

        self._viewport_rect = (vp_x, vp_y, vp_w, vp_h)

        # Auto-layout fallback for tests or direct paint calls
        if content.layout_rect is None:
            self.layout(width, height)

        # Get content geometry from layout
        rect = content.layout_rect
        if rect:
            rel_x, rel_y, content_w, content_h = rect
        else:
            # Fallback if layout not called
            if self.direction is ScrollDirection.VERTICAL:
                content_w, content_h = measure_preferred_size(content, max_width=vp_w)
            elif self.direction is ScrollDirection.HORIZONTAL:
                content_w, content_h = measure_preferred_size(content, max_height=vp_h)
            else:
                content_w, content_h = measure_preferred_size(content, max_width=vp_w, max_height=vp_h)
            rel_x, rel_y = pad_l, pad_t

        offset = self._controller.get_offset(self.direction)

        # Apply scroll offset to the base position
        if self.direction is ScrollDirection.VERTICAL:
            child_x = x + rel_x
            child_y = y + rel_y - int(offset)
        elif self.direction is ScrollDirection.HORIZONTAL:
            child_x = x + rel_x - int(offset)
            child_y = y + rel_y
        else:
            child_x = x + rel_x
            child_y = y + rel_y

        if canvas is None or not hasattr(canvas, "save") or not hasattr(canvas, "restore"):
            content.paint(canvas, child_x, child_y, content_w, content_h)
            return

        canvas.save()
        try:
            clip = make_rect(vp_x, vp_y, vp_w, vp_h)
            if clip is not None:
                clip_rect(canvas, clip, anti_alias=True)
            content.set_last_rect(child_x, child_y, content_w, content_h)
            content.paint(canvas, child_x, child_y, content_w, content_h)
        finally:
            try:
                canvas.restore()
            except Exception:
                exception_once(_logger, "scroll_viewport_canvas_restore_exc", "ScrollViewport canvas.restore failed")

    def hit_test(self, x: int, y: int):
        """Hit test in viewport-local coordinates.

        The app delivers pointer coordinates in root space, but `WidgetKernel.hit_test`
        translates them into each widget's local space while descending the tree.
        This method therefore receives (x, y) in this viewport's local coordinates.

        Since content is painted with a scroll offset, we must apply the inverse
        offset before delegating to the default child hit testing.
        """

        pad_l, pad_t, pad_r, pad_b = self._pad
        if hasattr(self, "_vp_size"):
            vp_w, vp_h = self._vp_size
        else:
            rect = self.layout_rect
            if rect is None:
                return None
            _rx, _ry, w, h = rect
            vp_w = max(0, int(w) - pad_l - pad_r)
            vp_h = max(0, int(h) - pad_t - pad_b)

        if not (pad_l <= x < pad_l + vp_w and pad_t <= y < pad_t + vp_h):
            return None

        offset = int(self._controller.get_offset(self.direction))
        if self.direction is ScrollDirection.VERTICAL:
            return super().hit_test(x, y + offset)
        if self.direction is ScrollDirection.HORIZONTAL:
            return super().hit_test(x + offset, y)
        return super().hit_test(x, y)

    def _update_scroll_metrics(self, content_w: int, content_h: int, vp_w: int, vp_h: int) -> None:
        if self.direction is ScrollDirection.VERTICAL:
            max_extent = max(0.0, content_h - vp_h)
            viewport_size = vp_h
            content_extent = content_h
        elif self.direction is ScrollDirection.HORIZONTAL:
            max_extent = max(0.0, content_w - vp_w)
            viewport_size = vp_w
            content_extent = content_w
        else:
            max_extent = 0.0
            viewport_size = vp_h
            content_extent = content_h
        self._controller._update_metrics(
            max_extent,
            viewport_size,
            content_extent,
            axis=self.direction,
        )


__all__ = ["ScrollViewport"]
