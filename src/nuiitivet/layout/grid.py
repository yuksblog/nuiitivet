from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from nuiitivet.common.logging_once import exception_once

from ..widgeting.widget import Widget
from ..rendering.sizing import Sizing, SizingLike, parse_sizing
from .container import Container
from .gap import normalize_gap
from .layout_utils import expand_layout_children


logger = logging.getLogger(__name__)

GridIndex = Union[int, Sequence[int]]


def _normalize_index(spec: Optional[GridIndex]) -> Tuple[Optional[int], int]:
    """Normalize row/column spec into (start, span)."""
    if spec is None:
        return None, 1
    if isinstance(spec, int):
        return spec, 1
    if isinstance(spec, Iterable):
        values = [int(v) for v in spec]
        if not values:
            return None, 1
        start = min(values)
        end = max(values)
        return start, end - start + 1
    raise TypeError("row/column spec must be int or iterable of ints")


@dataclass
class _ResolvedPlacement:
    child: Widget
    row: int
    column: int
    row_span: int
    column_span: int
    pref_width: int = 0
    pref_height: int = 0


class GridItem(Container):
    """Annotate a child with explicit grid placement data."""

    def __init__(
        self,
        child: Widget,
        *,
        row: Optional[GridIndex] = None,
        column: Optional[GridIndex] = None,
        area: Optional[str] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        align: Union[str, Tuple[str, str]] = "start",
    ):
        super().__init__(
            child=child,
            width=width,
            height=height,
            padding=padding,
            alignment=align,
        )
        self._row_spec = row
        self._column_spec = column
        self.area = area

    @classmethod
    def named_area(
        cls,
        name: str,
        child: Widget,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        align: Union[str, Tuple[str, str]] = "start",
    ) -> GridItem:
        """Create a GridItem placed in a named template area."""
        return cls(
            child=child,
            area=name,
            width=width,
            height=height,
            padding=padding,
            align=align,
        )

    def resolve_row(self) -> Tuple[Optional[int], int]:
        return _normalize_index(self._row_spec)

    def resolve_column(self) -> Tuple[Optional[int], int]:
        return _normalize_index(self._column_spec)


class Grid(Widget):
    """Two-dimensional layout container with explicit tracks."""

    def __init__(
        self,
        *,
        children: Optional[Sequence[Widget]] = None,
        areas: Optional[Sequence[Sequence[str]]] = None,
        rows: Optional[Sequence[SizingLike]] = None,
        columns: Optional[Sequence[SizingLike]] = None,
        row_gap: int = 0,
        column_gap: int = 0,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ):
        super().__init__(width=width, height=height, padding=padding)

        self._rows: List[Sizing] = [parse_sizing(d) for d in rows] if rows else []
        self._columns: List[Sizing] = [parse_sizing(d) for d in columns] if columns else []
        self.areas = self._normalize_areas(areas)
        self.row_gap = normalize_gap(row_gap)
        self.column_gap = normalize_gap(column_gap)

        if children:
            for child in children:
                self.add_child(child)

    @classmethod
    def named_areas(
        cls,
        *,
        areas: Sequence[Sequence[str]],
        children: Optional[Sequence[Widget]] = None,
        rows: Optional[Sequence[SizingLike]] = None,
        columns: Optional[Sequence[SizingLike]] = None,
        row_gap: int = 0,
        column_gap: int = 0,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ) -> Grid:
        """Create a Grid using named template areas."""
        return cls(
            children=children,
            areas=areas,
            rows=rows,
            columns=columns,
            row_gap=row_gap,
            column_gap=column_gap,
            width=width,
            height=height,
            padding=padding,
        )

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        l, t, r, b = self.padding
        child_max_w: Optional[int] = None
        child_max_h: Optional[int] = None
        if max_width is not None:
            child_max_w = max(0, int(max_width) - int(l) - int(r))
        elif self.width_sizing.kind == "fixed":
            child_max_w = max(0, int(self.width_sizing.value) - int(l) - int(r))
        if max_height is not None:
            child_max_h = max(0, int(max_height) - int(t) - int(b))
        elif self.height_sizing.kind == "fixed":
            child_max_h = max(0, int(self.height_sizing.value) - int(t) - int(b))

        placements, rows, columns = self._prepare_layout(child_max_w, child_max_h)
        if not rows:
            rows = [Sizing.auto()]
        if not columns:
            columns = [Sizing.auto()]

        row_sizes = self._measure_axis(rows, placements, "row", "row_span", "pref_height", self.row_gap)
        col_sizes = self._measure_axis(columns, placements, "column", "column_span", "pref_width", self.column_gap)

        content_w = sum(col_sizes) + self.column_gap * max(0, len(col_sizes) - 1)
        content_h = sum(row_sizes) + self.row_gap * max(0, len(row_sizes) - 1)

        w_dim = self.width_sizing
        h_dim = self.height_sizing

        width = int(w_dim.value) if w_dim.kind == "fixed" else content_w + l + r
        height = int(h_dim.value) if h_dim.kind == "fixed" else content_h + t + b

        if max_width is not None and w_dim.kind != "fixed":
            width = min(int(width), int(max_width))
        if max_height is not None and h_dim.kind != "fixed":
            height = min(int(height), int(max_height))
        return (int(width), int(height))

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        placements, rows, columns = self._prepare_layout()
        if not placements and not rows and not columns:
            return

        row_sizes = self._measure_axis(rows, placements, "row", "row_span", "pref_height", self.row_gap)
        col_sizes = self._measure_axis(columns, placements, "column", "column_span", "pref_width", self.column_gap)

        # Calculate content area size (relative to self at 0,0)
        l, t, r, b = self.padding
        cw = max(0, width - l - r)
        ch = max(0, height - t - b)

        row_sizes = self._apply_stretch(rows, row_sizes, self.row_gap, ch)
        col_sizes = self._apply_stretch(columns, col_sizes, self.column_gap, cw)

        # Start positions relative to self
        row_positions = self._accumulate_positions(t, row_sizes, self.row_gap)
        col_positions = self._accumulate_positions(l, col_sizes, self.column_gap)

        for placement in placements:
            row = placement.row
            col = placement.column
            if row >= len(row_sizes) or col >= len(col_sizes):
                continue
            row_end = min(row + placement.row_span, len(row_sizes))
            col_end = min(col + placement.column_span, len(col_sizes))

            # Calculate relative coordinates
            cell_y = row_positions[row]
            cell_x = col_positions[col]
            cell_h = sum(row_sizes[row:row_end]) + self.row_gap * max(0, row_end - row - 1)
            cell_w = sum(col_sizes[col:col_end]) + self.column_gap * max(0, col_end - col - 1)

            rect_x, rect_y = int(cell_x), int(cell_y)
            rect_w, rect_h = int(cell_w), int(cell_h)

            placement.child.layout(rect_w, rect_h)
            placement.child.set_layout_rect(rect_x, rect_y, rect_w, rect_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        self.set_last_rect(x, y, width, height)

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

    # --- helpers -------------------------------------------------
    def _prepare_layout(
        self,
        child_max_w: Optional[int] = None,
        child_max_h: Optional[int] = None,
    ) -> Tuple[List[_ResolvedPlacement], List[Sizing], List[Sizing]]:
        children = expand_layout_children(self.children_snapshot())
        rows = list(self._rows)
        columns = list(self._columns)
        placements: List[_ResolvedPlacement] = []

        for child in children:
            placement = self._resolve_child_placement(child, rows, columns)
            if placement is None:
                continue
            pref_w, pref_h = self._safe_preferred_size(child, child_max_w, child_max_h)
            placement.pref_width = max(0, int(pref_w))
            placement.pref_height = max(0, int(pref_h))
            placements.append(placement)

        return placements, rows, columns

    def _resolve_child_placement(
        self,
        child: Widget,
        rows: List[Sizing],
        columns: List[Sizing],
    ) -> Optional[_ResolvedPlacement]:
        if isinstance(child, GridItem):
            if child.area:
                row, column, row_span, column_span = self._area_to_rect(child.area)
            else:
                row_start, row_span = child.resolve_row()
                col_start, col_span = child.resolve_column()
                if row_start is None or col_start is None:
                    raise ValueError("GridItem requires 'area' or both 'row' and 'column' to be set")
                row = row_start
                column = col_start
                row_span = max(1, row_span)
                column_span = max(1, col_span)
        else:
            raise TypeError("Grid children must be GridItem instances with explicit placement")

        if row < 0 or column < 0:
            raise ValueError("Grid indices must be non-negative")

        self._ensure_track_length(rows, row + row_span)
        self._ensure_track_length(columns, column + column_span)
        return _ResolvedPlacement(child, row, column, row_span, column_span)

    def _safe_preferred_size(
        self,
        child: Widget,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        from .measure import preferred_size as measure_preferred_size

        try:
            return measure_preferred_size(child, max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(
                logger,
                "grid_preferred_size_exc",
                "child.preferred_size() failed (child=%s)",
                type(child).__name__,
            )
            return (0, 0)

    def _ensure_track_length(self, tracks: List[Sizing], required: int) -> None:
        while len(tracks) < required:
            tracks.append(Sizing.auto())

    def _measure_axis(
        self,
        dims: List[Sizing],
        placements: List[_ResolvedPlacement],
        start_attr: str,
        span_attr: str,
        pref_attr: str,
        spacing: int,
    ) -> List[float]:
        sizes = [dim.value if dim.kind == "fixed" else 0.0 for dim in dims]
        for placement in placements:
            start = getattr(placement, start_attr)
            span = getattr(placement, span_attr)
            pref = getattr(placement, pref_attr)
            if span <= 0:
                continue
            end = min(start + span, len(dims))
            if end <= start:
                continue

            fixed_total = 0.0
            dynamic_indices: List[int] = []
            for idx in range(start, end):
                dim = dims[idx]
                if dim.kind == "fixed":
                    fixed_total += sizes[idx]
                else:
                    dynamic_indices.append(idx)

            target = max(0.0, pref - spacing * max(0, span - 1) - fixed_total)
            if not dynamic_indices:
                continue
            current = sum(sizes[idx] for idx in dynamic_indices)
            if current >= target:
                continue
            extra = target - current
            per = extra / len(dynamic_indices)
            for idx in dynamic_indices:
                sizes[idx] += per

        return sizes

    def _apply_stretch(
        self,
        dims: List[Sizing],
        base_sizes: List[float],
        spacing: int,
        available: int,
    ) -> List[float]:
        if not base_sizes:
            return []
        total_spacing = spacing * max(0, len(base_sizes) - 1)
        usable = available - total_spacing
        sizes = list(base_sizes)
        if usable <= 0:
            return sizes

        current = sum(sizes)
        remaining = usable - current
        if remaining <= 0:
            # Not enough room; leave sizes as-is (children may overflow)
            return sizes

        weights = [dim.value if dim.kind == "flex" and dim.value > 0 else 0.0 for dim in dims]
        total_weight = sum(weights)
        if total_weight <= 0:
            return sizes

        unit = remaining / total_weight
        for idx, weight in enumerate(weights):
            if weight > 0:
                sizes[idx] += weight * unit
        return sizes

    def _accumulate_positions(self, start: int, sizes: List[float], spacing: int) -> List[float]:
        positions: List[float] = []
        cursor = float(start)
        for size in sizes:
            positions.append(cursor)
            cursor += size + spacing
        return positions

    def _normalize_areas(self, areas: Optional[Sequence[Sequence[str]]]) -> Optional[List[List[str]]]:
        if areas is None:
            return None
        normalized = [list(row) for row in areas]
        if not normalized:
            return None
        width = len(normalized[0])
        for row in normalized:
            if len(row) != width:
                raise ValueError("All area rows must have the same number of columns")
        return normalized

    def _area_to_rect(self, name: str) -> Tuple[int, int, int, int]:
        if not self.areas:
            raise ValueError("Grid has no areas defined")
        min_r, max_r = None, None
        min_c, max_c = None, None
        for r_idx, row in enumerate(self.areas):
            for c_idx, cell in enumerate(row):
                if cell == name:
                    if min_r is None or r_idx < min_r:
                        min_r = r_idx
                    if max_r is None or r_idx > max_r:
                        max_r = r_idx
                    if min_c is None or c_idx < min_c:
                        min_c = c_idx
                    if max_c is None or c_idx > max_c:
                        max_c = c_idx
        if min_r is None or min_c is None or max_r is None or max_c is None:
            raise ValueError(f"Grid area '{name}' is not defined")
        return min_r, min_c, max_r - min_r + 1, max_c - min_c + 1

    __all__ = ["Grid", "GridItem"]
