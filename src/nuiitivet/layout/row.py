"""Row layout: arrange children horizontally."""

from typing import List, Tuple, Optional, Union

from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from .gap import normalize_gap
from .metrics import compute_aligned_offsets, align_offset
from .layout_utils import expand_layout_children
from .for_each import ForEach, ItemsLike, BuilderFn
from .measure import preferred_size as measure_preferred_size


class Row(Widget):
    """Layout children horizontally.

    Parameters
    - gap: pixels between children
    - cross_alignment: 'start'|'center'|'end' for cross-axis (vertical) alignment
    - main_alignment: 'start'|'center'|'end'|'space-between'|'space-around'|'space-evenly'
    - padding: inner padding as int (all sides), (h, v), or (left, top, right, bottom)
    """

    # Hint for ancestor-based layout resolution (used by ForEach and others)
    layout_axis = "horizontal"

    def __init__(
        self,
        children: Optional[List[Widget]] = None,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        gap: int = 0,
        main_alignment: str = "start",
        cross_alignment: str = "start",
    ):
        """Initialize Row and configure layout.

        Args:
            children: List of child widgets to arrange horizontally.
            width: Row width. Defaults to None (shrinkwrap).
            height: Row height. Defaults to None (shrinkwrap).
            padding: Padding around the content.
            gap: Space between children in pixels.
            main_alignment: Horizontal alignment of children.
                'start', 'center', 'end', 'space-between', 'space-around', 'space-evenly'.
            cross_alignment: Vertical alignment of children.
                'start', 'center', 'end', 'stretch'.
        """
        super().__init__(width=width, height=height, padding=padding)
        if children:
            for c in children:
                self.add_child(c)
        self.gap = normalize_gap(gap)
        self.main_alignment = main_alignment
        self.cross_alignment = cross_alignment

    @classmethod
    def builder(
        cls,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        gap: int = 0,
        main_alignment: str = "start",
        cross_alignment: str = "start",
    ) -> "Row":
        """Create a Row that materializes children from items via ForEach.

        Args:
            items: Source data collection.
            builder: Function to create a widget for each item.
            width: Row width.
            height: Row height.
            padding: Padding around the content.
            gap: Space between children.
            main_alignment: Horizontal alignment of children.
            cross_alignment: Vertical alignment of children.
        """
        provider = ForEach(items, builder)
        return cls(
            children=[provider],
            width=width,
            height=height,
            padding=padding,
            gap=gap,
            main_alignment=main_alignment,
            cross_alignment=cross_alignment,
        )

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        children = expand_layout_children(self.children_snapshot())

        l, t, r, b = self.padding
        inner_max_h: Optional[int] = None
        if max_height is not None:
            inner_max_h = max(0, int(max_height) - int(t) - int(b))
        elif self.height_sizing.kind == "fixed":
            inner_max_h = max(0, int(self.height_sizing.value) - int(t) - int(b))

        widths: List[int] = []
        max_h = 0
        for c in children:
            w, h = measure_preferred_size(c, max_height=inner_max_h)
            widths.append(int(w))
            if int(h) > max_h:
                max_h = int(h)

        total_w = sum(widths) + max(0, len(widths) - 1) * self.gap

        # Add padding to content size
        content_width = total_w
        content_height = max_h

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
        children = expand_layout_children(self.children_snapshot())
        if not children:
            return

        # Calculate content area size (relative to self at 0,0)
        l, t, r, b = self.padding
        cw = max(0, width - l - r)
        ch = max(0, height - t - b)

        sizes = [measure_preferred_size(c, max_height=ch) for c in children]
        n = len(children)

        spacing = max(0, int(self.gap))
        spacing_total = max(0, n - 1) * spacing
        usable = max(0, cw - spacing_total)

        base_sizes: List[int] = []
        flex_weights: List[float] = []
        for idx, child in enumerate(children):
            pref_w = max(0, sizes[idx][0])
            dim = getattr(child, "width_sizing", None)
            if dim is None or dim.kind == "auto":
                base: int = pref_w
                flex: float = 0.0
            elif dim.kind == "fixed":
                base = max(0, int(dim.value))
                flex = 0.0
            else:  # flex
                base = 0
                flex = dim.value if dim.value > 0 else 1.0
            base_sizes.append(base)
            flex_weights.append(max(0.0, float(flex)))

        alloc = self._allocate_main_sizes(base_sizes, flex_weights, usable)
        col_offsets = compute_aligned_offsets(alloc, cw, spacing, self.main_alignment)

        # Content start offset (relative to self)
        cx, cy = l, t

        for idx, child in enumerate(children):
            w = alloc[idx]
            resolved_height = self._resolve_cross_size(child, sizes[idx][1], ch)

            # Check for child-specific cross-axis alignment override (CrossAligned/cross_align)
            child_align = getattr(child, "cross_align", None)
            alignment = str(child_align) if child_align else self.cross_alignment

            # Calculate relative position
            rel_y = cy + align_offset(ch, resolved_height, alignment)
            rel_x = cx + (col_offsets[idx] if idx < len(col_offsets) else 0)

            # Layout child and store geometry
            child.layout(w, resolved_height)
            child.set_layout_rect(rel_x, rel_y, w, resolved_height)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        children = expand_layout_children(self.children_snapshot())
        if not children:
            return

        # Auto-layout fallback for tests or direct paint calls
        if any(c.layout_rect is None for c in children):
            self.layout(width, height)

        for child in children:
            rect = child.layout_rect
            if rect is None:
                continue

            rel_x, rel_y, w, h = rect
            abs_x = x + rel_x
            abs_y = y + rel_y

            child.set_last_rect(abs_x, abs_y, w, h)

            child.paint(canvas, abs_x, abs_y, w, h)

    @staticmethod
    def _allocate_main_sizes(base_sizes: List[int], flex_weights: List[float], usable: int) -> List[int]:
        """Allocate main axis sizes with new Phase 1 rules.

        Priority:
        1. fixed/auto elements get their base_size (minimum, non-shrinkable)
        2. stretch elements share remaining space by weight
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
        minimum_total = sum(base for base, flex in zip(base_sizes, flex_weights) if flex == 0)

        # Phase 2: Allocate to fixed/auto first (guaranteed)
        alloc = base_sizes[:]
        remaining = usable - minimum_total

        # Phase 3: Distribute remaining space to flex elements
        total_flex = sum(flex_weights)
        if remaining > 0 and total_flex > 0:
            extras = [0] * n
            used = 0
            for idx, weight in enumerate(flex_weights):
                if weight <= 0:
                    continue
                share = int(weight / total_flex * remaining)
                extras[idx] = share
                used += share

            # Distribute remainder
            remainder = remaining - used
            if remainder > 0:
                for idx, weight in enumerate(flex_weights):
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
        dim = getattr(child, "height_sizing", None)
        if dim is None or dim.kind == "auto":
            target = pref
        elif dim.kind == "fixed":
            target = max(0, int(dim.value))
        else:  # flex
            target = available if available > 0 else pref
        if available > 0:
            target = min(target, available)
        return target
