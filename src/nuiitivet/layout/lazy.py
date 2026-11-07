"""Lazy materialization: a container holds widgets for the items in view and the ones around them."""

from __future__ import annotations

import logging
import math
from time import perf_counter
from typing import Any, Callable, List, Optional, Tuple

from nuiitivet.common.back_reference import back_reference
from nuiitivet.common.logging_once import exception_once

from ..widgeting.idle_work import cancel_idle_work, request_idle_work
from ..widgeting.widget import Widget
from .for_each import ForEach
from .layout_utils import expand_layout_children
from .measure import preferred_size as measure_preferred_size
from .scroll_viewport import ScrollViewport

logger = logging.getLogger(__name__)

# Items built ahead of the view in idle time, on each side at rest; the floor
# of the lead while scrolling.
MIN_AHEAD = 2
# While scrolling, the lead is the items one scroll step moves times this.
LEAD_STEPS = 3
MAX_AHEAD = 48
# A scroll older than this leaves the container at rest: the next direction is unknown.
REST_SECONDS = 0.25

PlaceFn = Callable[[Widget, int], None]


class LazyItems:
    """The item provider of a lazy container and the window it materializes.

    ``Column.lazy``, ``Row.lazy`` and ``UniformFlow.lazy`` each own one. It
    answers the item count, the one main-axis extent every item takes, the
    span of the container its scroll viewport shows, and the index range that
    span covers. While attached it keeps the container laid out as the viewport
    scrolls, and builds the items ahead of the view while the loop is idle.
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
        self._container_ref: Callable[[], Optional[Widget]] = back_reference(None)
        self._place: Optional[PlaceFn] = None
        self._visible: Tuple[int, int] = (0, 0)
        self._held: Tuple[int, int] = (0, 0)
        self._pitch = 0
        self._per_pitch = 1
        self._cross_limit: Optional[int] = None
        self._cross_limit_of_pass: Optional[int] = None
        self._direction = 0
        self._items_per_step = 0.0
        self._last_offset: Optional[float] = None
        self._last_scroll_at = 0.0
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
            self._held = (0, 1)
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

    def materialize(
        self,
        container: Widget,
        first: int,
        stop: int,
        *,
        pitch: int,
        place: PlaceFn,
        per_pitch: int = 1,
    ) -> Tuple[int, List[Widget]]:
        """Hold widgets for ``range(first, stop)`` and the built ones around it.

        The items in view that have no widget yet are built here. The ones
        around the view are kept while they lie within the lead, and the lead
        is filled in idle time.

        Args:
            container: The lazy container.
            first: The first item in view.
            stop: One past the last item in view.
            pitch: Pixels one item and its gap take along the axis.
            place: Lays one item out at its index; called for the items built
                in idle time.
            per_pitch: Items per pitch: the columns of a flow.

        Returns:
            The index of the first widget held and the widgets, in item order.
        """
        count = self.count()
        first = min(count, max(0, first))
        stop = min(count, max(first, stop))
        self._container_ref = back_reference(container)
        self._place = place
        self._pitch = max(0, int(pitch))
        self._per_pitch = max(1, int(per_pitch))
        self._visible = (first, stop)
        self._cross_limit_of_pass = self._cross_limit
        # The built items around the view stay while they lie within the lead;
        # an old range that no longer reaches the view is let go whole.
        old_first, old_stop = self._held
        lead = self._lead()
        held_first = max(first - lead, old_first) if old_first <= first <= old_stop else first
        held_stop = min(stop + lead, old_stop, count) if old_first <= stop <= old_stop else stop
        self._held = (held_first, held_stop)
        self.provider.set_window(held_first, held_stop)
        children = expand_layout_children(container.children_snapshot())
        if self._wants_more():
            request_idle_work(self._prefetch)
        return (held_first, children)

    def placed(self, child: Widget, main_position: int, cross_limit: int) -> bool:
        """Whether ``child`` is clean and laid out at ``main_position`` under ``cross_limit``.

        The cross limit is the one of the pass before, ``place`` having run
        under it; a pass under another limit places every item again.
        """
        self._cross_limit = cross_limit
        if cross_limit != self._cross_limit_of_pass or child.needs_layout:
            return False
        rect = child.layout_rect
        if rect is None:
            return False
        position = rect[1] if self.axis == "vertical" else rect[0]
        return position == main_position

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

    # ---- The lead ---------------------------------------------------------
    def _lead(self) -> int:
        """Items kept and built on a side of the view: at most one view's worth."""
        floor = MIN_AHEAD * self._per_pitch
        if self._direction == 0:
            return floor
        first, stop = self._visible
        lead = int(math.ceil(self._items_per_step * LEAD_STEPS))
        return max(floor, min(MAX_AHEAD, stop - first, lead))

    def _targets(self) -> Tuple[int, int]:
        """The range the held one grows toward in idle time."""
        count = self.count()
        first, stop = self._visible
        lead = self._lead()
        if self._direction > 0:
            return (max(0, first - MIN_AHEAD * self._per_pitch), min(count, stop + lead))
        if self._direction < 0:
            return (max(0, first - lead), min(count, stop + MIN_AHEAD * self._per_pitch))
        return (max(0, first - lead), min(count, stop + lead))

    def _wants_more(self) -> bool:
        target_first, target_stop = self._targets()
        held_first, held_stop = self._held
        return held_first > target_first or held_stop < target_stop

    def _prefetch(self, deadline: float) -> bool:
        """Build one item beyond the held range at a time, until the deadline."""
        container = self._container_ref()
        place = self._place
        if container is None or place is None:
            return False
        if perf_counter() - self._last_scroll_at > REST_SECONDS:
            self._direction = 0
        while perf_counter() < deadline:
            target_first, target_stop = self._targets()
            held_first, held_stop = self._held
            ahead = held_stop < target_stop
            behind = held_first > target_first
            if not ahead and not behind:
                return False
            # The scroll direction picks the side; at rest the side with fewer items built.
            built_ahead = held_stop - self._visible[1]
            built_behind = self._visible[0] - held_first
            if ahead and (self._direction > 0 or not behind or built_ahead <= built_behind):
                index = held_stop
                self._held = (held_first, held_stop + 1)
            else:
                index = held_first - 1
                self._held = (held_first - 1, held_stop)
            self.provider.set_window(*self._held)
            children = self.provider.window_children()
            position = index - self._held[0]
            if 0 <= position < len(children):
                place(children[position], index)
        return self._wants_more()

    # ---- Following the viewport ---------------------------------------------
    def attach(self, container: Widget) -> None:
        """Lay ``container`` out again on each scroll of its viewport."""
        self.detach()
        self._container_ref = back_reference(container)
        viewport, _ox, _oy = self._find_viewport(container)
        if viewport is None:
            return
        state = viewport.controller.axis_state(viewport.direction)
        try:
            self._last_offset = float(state.offset.value)
        except Exception:
            self._last_offset = None

        def _on_offset(value: float) -> None:
            self._note_scroll(value)
            target = self._container_ref()
            if target is not None:
                target.mark_needs_layout()

        try:
            self._offset_disposable = state.offset.subscribe(_on_offset)
        except Exception:
            exception_once(logger, "lazy_items_offset_subscribe_exc", "LazyItems offset subscribe failed")
            self._offset_disposable = None

    def _note_scroll(self, offset: float) -> None:
        last = self._last_offset
        self._last_offset = float(offset)
        self._last_scroll_at = perf_counter()
        if last is None or self._pitch <= 0:
            return
        delta = float(offset) - last
        if delta == 0.0:
            return
        self._direction = 1 if delta > 0 else -1
        self._items_per_step = abs(delta) / self._pitch * self._per_pitch

    def detach(self) -> None:
        """Stop following the viewport and building ahead of it."""
        cancel_idle_work(self._prefetch)
        self._place = None
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
