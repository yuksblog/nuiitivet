"""Column layout: arrange children vertically."""

from nuiitivet.widgeting.paint_replay import replay_safe
from typing import List, Tuple, Optional, Union, Sequence

from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from .gap import normalize_gap
from .metrics import compute_aligned_offsets, align_offset
from .layout_utils import expand_layout_children, layout_child_if_needed, paint_laid_out_children, sized_by_parent
from .for_each import ForEach, ItemsLike, BuilderFn, KeyFn
from .lazy import LazyItems
from .measure import preferred_size as measure_preferred_size
from nuiitivet.observable.protocols import StateBase


class Column(Widget):
    """Layout children vertically.

    From a data collection, or a State of one: :meth:`builder`. The
    items in view only, for a long list: :meth:`lazy`.
    """

    # Hint for ancestor-based layout resolution (used by ForEach and others)
    layout_axis = "vertical"

    def __init__(
        self,
        children: Optional[Sequence[Widget]] = None,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        gap: Union[int, StateBase] = 0,
        main_alignment: str = "start",
        cross_alignment: str = "start",
        key: Optional[str] = None,
    ):
        """Initialize Column and configure layout.

        Args:
            children: List of child widgets to arrange vertically.
            width: Column width.
            height: Column height.
            padding: Padding around the content.
            gap: Space between children in pixels.
            main_alignment: Vertical alignment of children.
                'start', 'center', 'end', 'space-between', 'space-around', 'space-evenly'.
            cross_alignment: Horizontal alignment of children.
                'start', 'center' or 'end'.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(width=width, height=height, padding=padding, key=key)
        if children:
            for c in children:
                self.add_child(c)

        self._gap = 0
        self.gap = gap  # type: ignore

        self.main_alignment = main_alignment
        self.cross_alignment = cross_alignment
        self._lazy: Optional[LazyItems] = None

    @property
    def gap(self) -> int:
        return getattr(self, "_gap", 0)

    @gap.setter
    def gap(self, value: Union[int, StateBase]) -> None:
        if isinstance(value, StateBase):
            if hasattr(self, "observe"):
                self.observe(value, lambda v: setattr(self, "gap", v))
            return
        self._gap = normalize_gap(value)
        self.mark_needs_layout()

    @classmethod
    def builder(
        cls,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        key_fn: Optional[KeyFn] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        gap: int = 0,
        main_alignment: str = "start",
        cross_alignment: str = "start",
        key: Optional[str] = None,
    ) -> "Column":
        """Create a Column whose children are built from *items*.

        Args:
            items: Source data: a collection, or a State of one -- the
                children then follow its changes.
            builder: Called as ``builder(item, index)`` for each item; returns
                the item's widget.
            key_fn: Called as ``key_fn(item, index)``; the result identifies
                the item across changes of *items*, so an item that moves keeps
                its widget. By index when omitted.
            width: Column width.
            height: Column height.
            padding: Padding around the content.
            gap: Space between children in pixels.
            main_alignment: Vertical alignment of children.
                'start', 'center', 'end', 'space-between', 'space-around', 'space-evenly'.
            cross_alignment: Horizontal alignment of children.
                'start', 'center' or 'end'.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        provider = ForEach(items, builder, key_fn=key_fn)
        return cls(
            children=[provider],
            width=width,
            height=height,
            padding=padding,
            gap=gap,
            main_alignment=main_alignment,
            cross_alignment=cross_alignment,
            key=key,
        )

    @classmethod
    def lazy(
        cls,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        key_fn: Optional[KeyFn] = None,
        item_height: Optional[int] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        gap: int = 0,
        cross_alignment: str = "start",
        key: Optional[str] = None,
    ) -> "Column":
        """Create a Column that holds widgets for the items in view and the ones around them.

        Inside a ``VerticalScrollable`` the Column builds the items the viewport
        shows, builds the next ones ahead of the scroll while the app is idle,
        and unmounts the ones that scrolled a view's length away; its height is the
        height of every item, so the scrollbar is exact. A frame short of time
        builds the items it can and the rest of the view stays blank until the
        app is idle. Outside a scrollable it holds the items inside
        its own rect. Every item takes the same height, and the Column takes the
        width it is offered.

        Args:
            items: Source data: a collection, or a State of one -- the
                children then follow its changes.
            builder: Called as ``builder(item, index)`` for an item entering
                the view; returns the item's widget.
            key_fn: Called as ``key_fn(item, index)``; the result identifies
                the item across changes of *items*, so an item that moves keeps
                its widget. By index when omitted.
            item_height: Height of every item in pixels. ``None`` measures the
                first item in view and gives its height to all.
            width: Column width.
            height: Column height.
            padding: Padding around the content.
            gap: Space between children in pixels.
            cross_alignment: Horizontal alignment of children.
                'start', 'center' or 'end'.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        provider = ForEach(items, builder, key_fn=key_fn)
        column = cls(
            children=[provider],
            width=width,
            height=height,
            padding=padding,
            gap=gap,
            cross_alignment=cross_alignment,
            key=key,
        )
        column._lazy = LazyItems(provider, "vertical", item_height)
        return column

    def on_mount(self) -> None:
        super().on_mount()
        if self._lazy is not None:
            self._lazy.attach(self)

    def on_unmount(self) -> None:
        if self._lazy is not None:
            self._lazy.detach()
        super().on_unmount()

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        if self._lazy is not None:
            return self._lazy_preferred_size(self._lazy, max_width, max_height)
        children = expand_layout_children(self.children_snapshot())

        l, t, r, b = self.padding
        inner_max_w: Optional[int] = None
        if max_width is not None:
            inner_max_w = max(0, int(max_width) - int(l) - int(r))
        elif self.width_sizing.kind == "fixed":
            inner_max_w = max(0, int(self.width_sizing.value) - int(l) - int(r))

        heights: List[int] = []
        max_w = 0
        for c in children:
            w, h = measure_preferred_size(c, max_width=inner_max_w)
            heights.append(int(h))
            if int(w) > max_w:
                max_w = int(w)

        total_h = sum(heights) + max(0, len(heights) - 1) * self.gap

        # Add padding to content size
        content_width = max_w
        content_height = total_h

        # Apply explicit sizing if provided
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = content_width + l + r
            if max_width is not None:
                width = min(width, int(max_width))

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = content_height + t + b
            if max_height is not None:
                height = min(height, int(max_height))

        return (width, height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        if self._lazy is not None:
            self._lazy_layout(self._lazy, width, height)
            return
        children = expand_layout_children(self.children_snapshot())
        self._laid_out_children = children
        if not children:
            return

        # Calculate content area size (relative to self at 0,0)
        l, t, r, b = self.padding
        cw = max(0, width - l - r)
        ch = max(0, height - t - b)

        # A child sized by the parent on both axes is placed without a measurement.
        sizes = [None if sized_by_parent(c) else measure_preferred_size(c, max_width=cw) for c in children]
        n = len(children)

        spacing = max(0, int(self.gap))
        spacing_total = max(0, n - 1) * spacing
        usable = max(0, ch - spacing_total)

        base_sizes: List[int] = []
        weights: List[float] = []
        for idx, child in enumerate(children):
            size = sizes[idx]
            pref_h = 0 if size is None else max(0, size[1])
            dim = getattr(child, "height_sizing", None)
            if dim is None or dim.kind == "auto":
                base: int = pref_h
                weight: float = 0.0
            elif dim.kind == "fixed":
                base = max(0, int(dim.value))
                weight = 0.0
            else:  # weight
                base = 0
                weight = dim.value if dim.value > 0 else 1.0
            base_sizes.append(base)
            weights.append(max(0.0, float(weight)))

        alloc = self._allocate_main_sizes(base_sizes, weights, usable)
        row_offsets = compute_aligned_offsets(alloc, ch, spacing, self.main_alignment)

        # Content start offset (relative to self)
        cx, cy = l, t

        for idx, child in enumerate(children):
            h = alloc[idx]
            size = sizes[idx]
            resolved_width = self._resolve_cross_size(child, 0 if size is None else size[0], cw)

            # Check for child-specific cross-axis alignment override (CrossAligned/cross_align)
            child_align = getattr(child, "cross_align", None)
            alignment = str(child_align) if child_align else self.cross_alignment

            # Calculate relative position
            rel_x = cx + align_offset(cw, resolved_width, alignment)
            rel_y = cy + (row_offsets[idx] if idx < len(row_offsets) else 0)

            # Layout child and store geometry
            layout_child_if_needed(child, resolved_width, h, sized_by_parent=size is None)
            child.set_layout_rect(rel_x, rel_y, resolved_width, h)

    @replay_safe
    def paint(self, canvas, x: int, y: int, width: int, height: int):
        paint_laid_out_children(self, canvas, x, y, width, height)

    def _lazy_preferred_size(
        self, lazy: LazyItems, max_width: Optional[int], max_height: Optional[int]
    ) -> Tuple[int, int]:
        l, t, r, b = self.padding
        inner_max_w: Optional[int] = None
        if max_width is not None:
            inner_max_w = max(0, int(max_width) - int(l) - int(r))
        elif self.width_sizing.kind == "fixed":
            inner_max_w = max(0, int(self.width_sizing.value) - int(l) - int(r))

        count = lazy.count()
        extent = lazy.known_extent() if count else 0
        content_height = 0 if extent is None else count * extent + max(0, count - 1) * self.gap

        w_dim = self.width_sizing
        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        elif max_width is not None:
            width = int(max_width)
        else:
            sample = lazy.sample_size(inner_max_w) if count else None
            width = (sample[0] if sample else 0) + l + r

        h_dim = self.height_sizing
        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = content_height + t + b
            if max_height is not None:
                height = min(height, int(max_height))
        return (width, height)

    def _lazy_layout(self, lazy: LazyItems, width: int, height: int) -> None:
        l, t, r, b = self.padding
        cw = max(0, width - l - r)

        count = lazy.count()
        extent = lazy.item_extent(self, cw) if count else 0
        span = lazy.visible_span(self, height)
        first, stop = lazy.index_range(span, count, extent, self.gap, t)
        pitch = extent + self.gap

        def place(child: Widget, index: int) -> None:
            pref_w, _ = measure_preferred_size(child, max_width=cw)
            resolved_width = self._resolve_cross_size(child, pref_w, cw)
            child_align = getattr(child, "cross_align", None)
            alignment = str(child_align) if child_align else self.cross_alignment
            rel_x = l + align_offset(cw, resolved_width, alignment)
            layout_child_if_needed(child, resolved_width, extent)
            child.set_layout_rect(rel_x, t + index * pitch, resolved_width, extent)

        start, children = lazy.materialize(self, first, stop, pitch=pitch, place=place)
        self._laid_out_children = children
        for i, child in enumerate(children):
            # A clean item already at its slot, from an earlier pass or from
            # idle time, is left as it is.
            if lazy.placed(child, t + (start + i) * pitch, cw):
                continue
            place(child, start + i)

    @staticmethod
    def _allocate_main_sizes(base_sizes: List[int], weights: List[float], usable: int) -> List[int]:
        """Allocate main axis sizes with new Phase 1 rules.

        Priority:
        1. fixed/auto elements get their base_size (minimum, non-shrinkable)
        2. weight elements share remaining space by weight
        3. If not enough space, fixed/auto may overflow (spacing/padding are guaranteed)
        """
        n = len(base_sizes)
        if n == 0:
            return []
        usable = max(0, int(usable))
        base_sizes = [max(0, int(b)) for b in base_sizes]

        if usable == 0:
            return [0] * n

        # Phase 1: Calculate minimum requirements (fixed/auto)
        minimum_total = sum(base for base, weight in zip(base_sizes, weights) if weight == 0)

        # Phase 2: Allocate to fixed/auto first (guaranteed)
        alloc = base_sizes[:]
        remaining = usable - minimum_total

        # Phase 3: Distribute remaining space to weight elements
        total_weight = sum(weights)
        if remaining > 0 and total_weight > 0:
            extras = [0] * n
            used = 0
            for idx, weight in enumerate(weights):
                if weight <= 0:
                    continue
                share = int(weight / total_weight * remaining)
                extras[idx] = share
                used += share

            # Distribute remainder
            remainder = remaining - used
            if remainder > 0:
                for idx, weight in enumerate(weights):
                    if weight > 0 and remainder > 0:
                        extras[idx] += 1
                        remainder -= 1
                    if remainder == 0:
                        break

            for idx in range(n):
                alloc[idx] += extras[idx]

        # Note: If remaining < 0, fixed/auto will overflow (by design)
        # Phase 2 (overflow strategies) will handle clipping/scrolling

        return alloc

    @staticmethod
    def _resolve_cross_size(child: Widget, pref: int, available: int) -> int:
        pref = max(0, pref)
        available = max(0, available)
        dim = getattr(child, "width_sizing", None)
        if dim is None or dim.kind == "auto":
            target = pref
        elif dim.kind == "fixed":
            target = max(0, int(dim.value))
        else:  # weight
            target = available if available > 0 else pref
        if available > 0:
            target = min(target, available)
        return target
