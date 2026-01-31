"""Flow layout: arrange children in a wrapping flow or uniform grid."""

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


class Flow(Widget):
    """Layout children in rows that wrap or in a uniform grid.

    Warning:
        This API is **provisional** and subject to change.
        The `uniform` mode and its related parameters (`columns`, `aspect_ratio`, etc.)
        may be moved to a separate `UniformFlow` or `Grid` widget in future versions.
    """

    def __init__(
        self,
        children: Optional[Sequence[Widget]] = None,
        *,
        uniform: bool = False,
        main_gap: int = 0,
        cross_gap: int = 0,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        align: str = "start",
        run_align: str = "start",
        item_align: str = "start",
        cell_align: AlignValue = "stretch",
        columns: Optional[int] = None,
        max_column_width: Optional[int] = None,
        aspect_ratio: Optional[float] = None,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        super().__init__(width=width, height=height, padding=padding)
        if children:
            for child in children:
                self.add_child(child)

        self.uniform = bool(uniform)
        self.main_gap = normalize_gap(main_gap)
        self.cross_gap = normalize_gap(cross_gap)
        self.align = align or "start"
        self.run_align = run_align or "start"
        self.item_align = item_align or "start"
        self._cell_align = self._normalize_align_pair(cell_align)
        self.columns = self._normalize_positive(columns)
        self.max_column_width = self._normalize_positive(max_column_width)
        self.aspect_ratio = float(aspect_ratio) if aspect_ratio else None

    @classmethod
    def builder(
        cls,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        uniform: bool = False,
        main_gap: int = 0,
        cross_gap: int = 0,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        align: str = "start",
        run_align: str = "start",
        item_align: str = "start",
        cell_align: AlignValue = "stretch",
        columns: Optional[int] = None,
        max_column_width: Optional[int] = None,
        aspect_ratio: Optional[float] = None,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> "Flow":
        """Create a Flow that materializes children from items via ForEach."""

        provider = ForEach(items, builder)
        return cls(
            [provider],
            uniform=uniform,
            main_gap=main_gap,
            cross_gap=cross_gap,
            padding=padding,
            align=align,
            run_align=run_align,
            item_align=item_align,
            cell_align=cell_align,
            columns=columns,
            max_column_width=max_column_width,
            aspect_ratio=aspect_ratio,
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

        if self.uniform:
            width, height = self._preferred_size_uniform(children, inner_max_w)
        else:
            width, height = self._preferred_size_flow(children, inner_max_w)

        width = self._resolve_sizing(self.width_sizing, width + pad[0] + pad[2])
        height = self._resolve_sizing(self.height_sizing, height + pad[1] + pad[3])

        if max_width is not None and self.width_sizing.kind != "fixed":
            width = min(width, int(max_width))
        if max_height is not None and self.height_sizing.kind != "fixed":
            height = min(height, int(max_height))

        return (int(width), int(height))

    def _preferred_size_uniform(self, children: List[Widget], inner_max_w: Optional[int]) -> Tuple[int, int]:
        count = len(children)
        if inner_max_w is not None and inner_max_w > 0:
            cols = self._resolve_columns(count, inner_max_w)
        else:
            cols = self._intrinsic_columns(count)
        rows = max(1, math.ceil(count / max(1, cols)))

        max_w = 0
        max_h = 0
        for child in children:
            pref_w, pref_h = measure_preferred_size(child, max_width=inner_max_w)
            max_w = max(max_w, max(0, pref_w))
            max_h = max(max_h, max(0, pref_h))
        if self.aspect_ratio and max_w > 0:
            max_h = max(max_h, self._height_from_aspect(max_w))

        content_w = cols * max_w + max(0, cols - 1) * self.main_gap
        content_h = rows * max_h + max(0, rows - 1) * self.cross_gap
        return (int(content_w), int(content_h))

    def _preferred_size_flow(self, children: List[Widget], inner_max_w: Optional[int]) -> Tuple[int, int]:
        if inner_max_w is None or inner_max_w <= 0:
            total_w = 0
            max_h = 0
            for idx, child in enumerate(children):
                pref_w, pref_h = child.preferred_size()
                if idx > 0:
                    total_w += self.main_gap
                total_w += max(0, int(pref_w))
                max_h = max(max_h, max(0, int(pref_h)))
            return (int(total_w), int(max_h))

        row_w = 0
        row_h = 0
        max_row_w = 0
        total_h = 0
        first_in_row = True

        for child in children:
            pref_w, pref_h = measure_preferred_size(child, max_width=inner_max_w)
            cw = max(0, int(pref_w))
            ch = max(0, int(pref_h))

            extra_gap = 0 if first_in_row else self.main_gap
            next_w = row_w + extra_gap + cw

            if not first_in_row and next_w > inner_max_w:
                total_h += row_h
                total_h += self.cross_gap
                max_row_w = max(max_row_w, row_w)
                row_w = cw
                row_h = ch
                first_in_row = False
                continue

            row_w = next_w if not first_in_row else cw
            row_h = max(row_h, ch)
            first_in_row = False

        if not first_in_row:
            total_h += row_h
            max_row_w = max(max_row_w, row_w)

        return (min(int(inner_max_w), int(max_row_w or inner_max_w)), int(total_h))

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
        # Content area relative to self (0,0)
        inner_x = pad[0]
        inner_y = pad[1]
        inner_w = max(0, width - pad[0] - pad[2])
        inner_h = max(0, height - pad[1] - pad[3])

        if self.uniform:
            self._layout_uniform(children, inner_x, inner_y, inner_w, inner_h)
        else:
            self._layout_flow(children, inner_x, inner_y, inner_w, inner_h)

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

    def _layout_uniform(self, children: List[Widget], x: int, y: int, w: int, h: int) -> None:
        count = len(children)
        cols = self._resolve_columns(count, w)
        cols = max(1, cols)
        rows = max(1, math.ceil(count / cols))

        col_widths = self._resolve_column_widths(cols, w, children)
        row_heights = self._resolve_row_heights(rows, col_widths, children)

        content_w = sum(col_widths) + max(0, cols - 1) * self.main_gap
        content_h = sum(row_heights) + max(0, rows - 1) * self.cross_gap

        start_x = x + align_offset(w, content_w, self.align)
        start_y = y + align_offset(h, content_h, self.run_align)

        col_offsets = compute_prefix_offsets(col_widths, self.main_gap)
        row_offsets = compute_prefix_offsets(row_heights, self.cross_gap)

        sizes = [measure_preferred_size(child, max_width=w, max_height=h) for child in children]

        for i, child in enumerate(children):
            r = i // cols
            c = i % cols

            cell_w = col_widths[c]
            cell_h = row_heights[r]

            # Calculate relative position
            cell_x = start_x + col_offsets[c]
            cell_y = start_y + row_offsets[r]

            pref_w, pref_h = sizes[i]

            # Apply cell alignment
            child_w = cell_w
            child_h = cell_h

            # Handle alignment within the cell
            align_x, align_y = self._cell_align

            if align_x != "stretch":
                child_w = min(pref_w, cell_w)
                cell_x += align_offset(cell_w, child_w, align_x)

            if align_y != "stretch":
                child_h = min(pref_h, cell_h)
                cell_y += align_offset(cell_h, child_h, align_y)

            child.layout(child_w, child_h)
            child.set_layout_rect(int(cell_x), int(cell_y), int(child_w), int(child_h))

    def _layout_flow(self, children: List[Widget], x: int, y: int, w: int, h: int) -> None:
        # Simple flow layout implementation
        # This logic was previously embedded in _paint_flow but needs to be extracted
        # Since _paint_flow wasn't fully implemented in the snippet, we'll implement a basic version here
        # that matches the expected behavior of a wrapping flow layout.

        current_x = x

        # First pass: measure and group into rows
        rows: list[tuple[list[tuple[Widget, int, int]], int, int]] = []
        current_row: list[tuple[Widget, int, int]] = []
        current_row_width = 0
        current_row_height = 0

        for child in children:
            cw, ch = measure_preferred_size(child, max_width=w, max_height=h)

            if current_row and (current_x + cw > x + w) and w > 0:
                # Wrap to next row
                rows.append((current_row, current_row_width, current_row_height))
                current_row = []
                current_x = x
                current_row_width = 0
                current_row_height = 0

            current_row.append((child, cw, ch))
            current_row_width += cw + (self.main_gap if len(current_row) > 1 else 0)
            current_row_height = max(current_row_height, ch)
            current_x += cw + self.main_gap

        if current_row:
            rows.append((current_row, current_row_width, current_row_height))

        # Second pass: position rows and children
        # Calculate total content height for run_align
        total_content_h = sum(r[2] for r in rows) + max(0, len(rows) - 1) * self.cross_gap
        start_y = y + align_offset(h, total_content_h, self.run_align)

        current_y = start_y
        for row_items, row_w, row_h in rows:
            # Calculate row start x based on align
            start_x = x + align_offset(w, row_w, self.align)
            current_x = start_x

            for child, cw, ch in row_items:
                # Apply item alignment within the row height
                child_y = current_y + align_offset(row_h, ch, self.item_align)

                child.layout(cw, ch)
                child.set_layout_rect(int(current_x), int(child_y), int(cw), int(ch))

                current_x += cw + self.main_gap

            current_y += row_h + self.cross_gap

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
            pref_w, pref_h = child.preferred_size()
            row = min(idx // cols, rows - 1)
            if self.aspect_ratio and col_widths:
                col = idx % len(col_widths)
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

    def _resolve_child_size_uniform(self, pref_w: int, pref_h: int, cell_w: int, cell_h: int) -> Tuple[int, int]:
        cell_w = max(0, cell_w)
        cell_h = max(0, cell_h)
        pref_w = max(0, pref_w)
        pref_h = max(0, pref_h)

        if self._cell_align[0] == "stretch" or cell_w == 0:
            child_w = cell_w
        else:
            child_w = min(pref_w if pref_w > 0 else cell_w, cell_w)

        if self._cell_align[1] == "stretch" or cell_h == 0:
            if self.aspect_ratio and child_w > 0:
                child_h = self._height_from_aspect(child_w)
                child_h = min(child_h, cell_h) if cell_h > 0 else child_h
            else:
                child_h = cell_h
        else:
            child_h = min(pref_h if pref_h > 0 else cell_h, cell_h)
        return (child_w, child_h)
