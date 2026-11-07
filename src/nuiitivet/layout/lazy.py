"""Lazy materialization: a container holds widgets for the items in view only."""

from __future__ import annotations

import logging
import math
from typing import Any, List, Optional, Tuple

from nuiitivet.common.logging_once import exception_once

from ..widgeting.widget import Widget
from .for_each import ForEach
from .layout_utils import expand_layout_children
from .measure import preferred_size as measure_preferred_size
from .scroll_viewport import ScrollViewport

logger = logging.getLogger(__name__)


class LazyItems:
    """The item provider of a lazy container and the window it materializes.

    ``Column.lazy``, ``Row.lazy`` and ``UniformFlow.lazy`` each own one. It
    answers the item count, the one main-axis extent every item takes, the
    span of the container its scroll viewport shows, and the index range that
    span covers. While attached it keeps the container laid out as the viewport
    scrolls.
    """

    def __init__(self, provider: ForEach, axis: str, extent: Optional[int]) -> None:
        """Initialize LazyItems.

        Args:
            provider: The ForEach that builds the items.
            axis: ``"vertical"`` or ``"horizontal"``: the axis the items run along.
            extent: Main-axis length of every item, in pixels; ``None`` measures
                the first item in view and gives its length to all.
        """
        self.provider = provider
        self.axis = axis
        self._given_extent: Optional[int] = None if extent is None else max(0, int(extent))
        self._offset_disposable: Optional[Any] = None
        # An empty window from the start: a mount before the first layout
        # builds nothing instead of every item.
        provider.set_window(0, 0)

    # ---- Items -----------------------------------------------------------
    def count(self) -> int:
        """The number of items."""
        return self.provider.item_count()

    def sample_size(self, cross_limit: Optional[int]) -> Tuple[int, int]:
        """Measure one item under ``cross_limit`` on the cross axis.

        The item is the first one in the current window; with no window yet,
        item 0 is materialized for it.
        """
        children = self.provider.window_children()
        if not children:
            self.provider.set_window(0, 1)
            children = self.provider.window_children()
        if not children:
            return (0, 0)
        sample = children[0]
        if self.axis == "vertical":
            w, h = measure_preferred_size(sample, max_width=cross_limit)
        else:
            w, h = measure_preferred_size(sample, max_height=cross_limit)
        return (max(0, int(w)), max(0, int(h)))

    def item_extent(self, cross_limit: Optional[int]) -> int:
        """The main-axis length of every item: the given one, else the sample's."""
        if self._given_extent is not None:
            return self._given_extent
        w, h = self.sample_size(cross_limit)
        return h if self.axis == "vertical" else w

    def materialize(self, container: Widget, first: int, stop: int) -> List[Widget]:
        """Hold widgets for ``range(first, stop)`` only and return them in order."""
        self.provider.set_window(first, stop)
        return expand_layout_children(container.children_snapshot())

    # ---- The window --------------------------------------------------------
    def visible_span(self, container: Widget, length: int) -> Tuple[int, int]:
        """The part of ``container``, along the axis, that its scroll viewport shows.

        Measured from the container's origin with the layout positions of the
        last pass. The whole ``length`` when no viewport encloses the container.
        """
        length = max(0, int(length))
        viewport, origin_x, origin_y = self._find_viewport(container)
        if viewport is None:
            return (0, length)
        clip_x, clip_y, clip_w, clip_h = viewport.visual_clip_rect()
        shift_x, shift_y = viewport.visual_offset()
        if self.axis == "vertical":
            start = clip_y - shift_y - origin_y
            end = start + clip_h
        else:
            start = clip_x - shift_x - origin_x
            end = start + clip_w
        lo = min(length, max(0, int(math.floor(start))))
        hi = min(length, max(lo, int(math.ceil(end))))
        return (lo, hi)

    @staticmethod
    def index_range(span: Tuple[int, int], count: int, extent: int, gap: int, pad_start: int) -> Tuple[int, int]:
        """The items whose slot touches ``span``, as ``(first, stop)``.

        Item ``i`` sits at ``pad_start + i * (extent + gap)``. Every item when
        the pitch is zero.
        """
        if count <= 0:
            return (0, 0)
        pitch = int(extent) + int(gap)
        if pitch <= 0:
            return (0, count)
        start, end = span
        if end <= start:
            return (0, 0)
        first = min(count, max(0, (int(start) - int(pad_start)) // pitch))
        stop = min(count, -(-(int(end) - int(pad_start)) // pitch))
        return (first, max(first, stop))

    # ---- Following the viewport ---------------------------------------------
    def attach(self, container: Widget) -> None:
        """Lay ``container`` out again on each scroll of its viewport."""
        self.detach()
        viewport, _ox, _oy = self._find_viewport(container)
        if viewport is None:
            return
        state = viewport.controller.axis_state(viewport.direction)

        def _on_offset(_value: float) -> None:
            container.mark_needs_layout()

        try:
            self._offset_disposable = state.offset.subscribe(_on_offset)
        except Exception:
            exception_once(logger, "lazy_items_offset_subscribe_exc", "LazyItems offset subscribe failed")
            self._offset_disposable = None

    def detach(self) -> None:
        """Stop following the viewport."""
        disposable = self._offset_disposable
        self._offset_disposable = None
        if disposable is None:
            return
        try:
            dispose = getattr(disposable, "dispose", None)
            if callable(dispose):
                dispose()
            elif callable(disposable):
                disposable()
        except Exception:
            exception_once(logger, "lazy_items_offset_dispose_exc", "LazyItems offset dispose failed")

    @staticmethod
    def _find_viewport(container: Widget) -> Tuple[Optional[ScrollViewport], int, int]:
        """The nearest enclosing viewport and the container's origin inside its content."""
        origin_x = origin_y = 0
        node: Any = container
        visited: set[int] = set()
        while node is not None and not isinstance(node, ScrollViewport):
            if id(node) in visited:
                return (None, 0, 0)
            visited.add(id(node))
            rect = getattr(node, "layout_rect", None)
            if rect is not None:
                origin_x += int(rect[0])
                origin_y += int(rect[1])
            node = getattr(node, "parent", None)
        if node is None:
            return (None, 0, 0)
        return (node, origin_x, origin_y)


__all__ = ["LazyItems"]
