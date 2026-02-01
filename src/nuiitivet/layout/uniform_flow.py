"""UniformFlow layout: arrange children in a grid with uniform column widths."""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple, Union

from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from .gap import normalize_gap
from .layout_utils import expand_layout_children
from .metrics import align_offset, compute_prefix_offsets
from .for_each import ForEach, ItemsLike, BuilderFn
from .measure import preferred_size as measure_preferred_size

AlignValue = Union[str, Tuple[str, str]]


class UniformFlow(Widget):
    """Layout children in a uniform grid.

    This layout arranges children into columns with equal width.
    """

    def __init__(
        self,
        children: Optional[Sequence[Widget]] = None,
        *,
        columns: Optional[int] = None,
        max_column_width: Optional[int] = None,
        aspect_ratio: Optional[float] = None,
        main_gap: int = 0,
        cross_gap: int = 0,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        main_alignment: str = "start",
        run_alignment: str = "start",
        item_alignment: AlignValue = "stretch",
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        super().__init__(width=width, height=height, padding=padding)
        if children:
            for child in children:
                self.add_child(child)

        self.columns = self._normalize_positive(columns)
        self.max_column_width = self._normalize_positive(max_column_width)
        self.aspect_ratio = float(aspect_ratio) if aspect_ratio else None
        self.main_gap = normalize_gap(main_gap)
        self.cross_gap = normalize_gap(cross_gap)
        self.main_alignment = main_alignment or "start"
        self.run_alignment = run_alignment or "start"
        self.item_alignment = self._normalize_align_pair(item_alignment)

    @classmethod
    def builder(
        cls,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        columns: Optional[int] = None,
        max_column_width: Optional[int] = None,
        aspect_ratio: Optional[float] = None,
        main_gap: int = 0,
        cross_gap: int = 0,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        main_alignment: str = "start",
        run_alignment: str = "start",
        item_alignment: AlignValue = "stretch",
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> "UniformFlow":
        """Create a UniformFlow that materializes children from items via ForEach."""
        provider = ForEach(items, builder)
        return cls(
            [provider],
            columns=columns,
            max_column_width=max_column_width,
            aspect_ratio=aspect_ratio,
            main_gap=main_gap,
            cross_gap=cross_gap,
            padding=padding,
            main_alignment=main_alignment,
            run_alignment=run_alignment,
            item_alignment=item_alignment,
            width=width,
            height=height,
        )

    @staticmethod
    def _normalize_positive(value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        iv = int(value)
        return iv if iv > 0 else None

    @staticmethod
    def _normalize_align_pair(value: AlignValue) -> Tuple[str, str]:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return (str(value[0]), str(value[1]))
        if isinstance(value, str):
            return (value, value)
        return ("stretch", "stretch")

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        children = expand_layout_children(self.children_snapshot())
        pad = self.padding

        if not children:
            width = pad[0] + pad[2]
            height = pad[1] + pad[3]
            if max_width is not None and self.width_sizing.kind != "fixed":
                width = min(width, int(max_width))
            if max_height is not None and self.height_sizing.kind != "fixed":
                height = min(height, int(max_height))
            return (width, height)

        inner_max_w: Optional[int] = None
        if max_width is not None:
            inner_max_w = max(0, int(max_width) - int(pad[0]) - int(pad[2]))
        elif self.width_sizing.kind == "fixed":
            inner_max_w = max(0, int(self.width_sizing.value) - int(pad[0]) - int(pad[2]))

        width, height = self._preferred_size_content(children, inner_max_w)

        width = self._resolve_sizing(self.width_sizing, width + pad[0] + pad[2])
        height = self._resolve_sizing(self.height_sizing, height + pad[1] + pad[3])

        if max_width is not None and self.width_sizing.kind != "fixed":
            width = min(width, int(max_width))
        if max_height is not None and self.height_sizing.kind != "fixed":
            height = min(height, int(max_height))

        return (int(width), int(height))

    def _preferred_size_content(self, children: List[Widget], inner_max_w: Optional[int]) -> Tuple[int, int]:
        count = len(children)
        col_limit: Optional[int] = inner_max_w
        if inner_max_w is not None and inner_max_w > 0:
            cols = self._resolve_columns(count, inner_max_w)
            # Calculate implied column width
            usable = max(0, inner_max_w - max(0, cols - 1) * self.main_gap)
            if usable > 0:
                col_limit = usable // cols
        else:
            cols = self._intrinsic_columns(count)
        rows = max(1, math.ceil(count / max(1, cols)))

        max_w = 0
        max_h = 0
        for child in children:
            pref_w, pref_h = measure_preferred_size(child, max_width=col_limit)
            max_w = max(max_w, max(0, pref_w))
            max_h = max(max_h, max(0, pref_h))
        if self.aspect_ratio and max_w > 0:
            max_h = max(max_h, self._height_from_aspect(max_w))

        content_w = cols * max_w + max(0, cols - 1) * self.main_gap
        content_h = rows * max_h + max(0, rows - 1) * self.cross_gap
        return (int(content_w), int(content_h))

    @staticmethod
    def _resolve_sizing(dim, fallback: int) -> int:
        if dim.kind == "fixed":
            return int(dim.value)
        return fallback

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        children = expand_layout_children(self.children_snapshot())
        if not children:
            return

        pad = self.padding
        inner_w = max(0, width - pad[0] - pad[2])
        inner_h = max(0, height - pad[1] - pad[3])

        count = len(children)
        cols = self._resolve_columns(count, inner_w)
        cols = max(1, cols)
        rows = max(1, math.ceil(count / cols))

        col_widths = self._resolve_column_widths(cols, inner_w, children)
        row_heights = self._resolve_row_heights(rows, col_widths, children)

        content_w = sum(col_widths) + max(0, cols - 1) * self.main_gap
        content_h = sum(row_heights) + max(0, rows - 1) * self.cross_gap

        start_x = pad[0] + align_offset(inner_w, content_w, self.main_alignment)
        start_y = pad[1] + align_offset(inner_h, content_h, self.run_alignment)

        col_offsets = compute_prefix_offsets(col_widths, self.main_gap)
        row_offsets = compute_prefix_offsets(row_heights, self.cross_gap)

        for i, child in enumerate(children):
            r = i // cols
            c = i % cols

            cell_w = col_widths[c]
            cell_h = row_heights[r]

            cell_x = start_x + col_offsets[c]
            cell_y = start_y + row_offsets[r]

            pref_w, pref_h = measure_preferred_size(child, max_width=cell_w)

            child_w = cell_w
            child_h = cell_h

            align_x, align_y = self.item_alignment

            if align_x != "stretch":
                child_w = min(pref_w, cell_w)
                cell_x += align_offset(cell_w, child_w, align_x)

            if align_y != "stretch":
                child_h = min(pref_h, cell_h)
                cell_y += align_offset(cell_h, child_h, align_y)

            child.layout(child_w, child_h)
            child.set_layout_rect(int(cell_x), int(cell_y), int(child_w), int(child_h))

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
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

    def _intrinsic_columns(self, child_count: int) -> int:
        if self.columns:
            return max(1, min(child_count, self.columns))
        if self.max_column_width:
            guess = int(math.sqrt(child_count)) or 1
            return max(1, min(child_count, guess))
        return max(1, child_count)

    def _resolve_columns(self, child_count: int, available_width: int) -> int:
        if self.columns:
            return max(1, min(child_count, self.columns))
        if self.max_column_width and available_width > 0:
            denom = self.max_column_width + self.main_gap
            if denom > 0:
                cols = max(1, (available_width + self.main_gap) // denom)
                return max(1, min(child_count, cols))
        return max(1, child_count)

    def _resolve_column_widths(self, cols: int, inner_w: int, children: List[Widget]) -> List[int]:
        if cols <= 0:
            return []
        usable = max(0, inner_w - max(0, cols - 1) * self.main_gap)
        if usable > 0:
            base = usable // cols
            rem = usable - base * cols
            widths = [base] * cols
            for i in range(rem):
                widths[i % cols] += 1
            return widths
        widths = [0] * cols
        for idx, child in enumerate(children):
            col = idx % cols
            pref_w, _ = child.preferred_size()
            widths[col] = max(widths[col], max(0, pref_w))
        return widths

    def _resolve_row_heights(self, rows: int, col_widths: List[int], children: List[Widget]) -> List[int]:
        if rows <= 0:
            return []
        heights = [0] * rows
        cols = max(1, len(col_widths))
        for idx, child in enumerate(children):
            col = idx % cols
            cw = col_widths[col] if col < len(col_widths) else None
            pref_w, pref_h = measure_preferred_size(child, max_width=cw)
            row = min(idx // cols, rows - 1)
            if self.aspect_ratio and col_widths:
                # col is already defined above
                tile_h = self._height_from_aspect(col_widths[col])
                heights[row] = max(heights[row], tile_h)
            else:
                heights[row] = max(heights[row], max(0, pref_h))
        if self.aspect_ratio and col_widths:
            default_h = self._height_from_aspect(col_widths[0])
            heights = [h if h > 0 else default_h for h in heights]
        return heights

    def _height_from_aspect(self, width: int) -> int:
        if not self.aspect_ratio or self.aspect_ratio <= 0:
            return max(0, width)
        return max(1, int(round(width / self.aspect_ratio)))
