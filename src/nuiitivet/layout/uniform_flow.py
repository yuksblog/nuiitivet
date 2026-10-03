"""UniformFlow layout: arrange children in a grid with uniform column widths."""

from __future__ import annotations

from nuiitivet.widgeting.paint_replay import replay_safe
import math
from typing import List, Optional, Sequence, Tuple, Union

from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from .gap import normalize_gap
from .layout_utils import expand_layout_children, paint_laid_out_children
from .metrics import align_offset, compute_prefix_offsets
from .for_each import ForEach, ItemsLike, BuilderFn
from .measure import preferred_size as measure_preferred_size

AlignValue = Union[str, Tuple[str, str]]


class UniformFlow(Widget):
    """Layout children in a uniform grid.

    This layout arranges children into columns with equal width. A row is as
    tall as its tallest child measures; a row whose children all have a ``"wt"``
    height also takes a share of the height the other rows leave.

    From a data collection, or an observable of one: :meth:`builder`.
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
        item_alignment: AlignValue = "start",
        width: SizingLike = None,
        height: SizingLike = None,
        key: Optional[str] = None,
    ) -> None:
        """Initialize UniformFlow.

        Args:
            children: Child widgets to arrange.
            columns: Number of columns. Takes precedence over *max_column_width*.
            max_column_width: Widest a column may get, in pixels; as many columns
                as fit the available width are used. With neither this nor
                *columns*, every child sits in one row.
            aspect_ratio: Cell width divided by cell height; sets a minimum cell
                height from the column width.
            main_gap: Space between columns, in pixels.
            cross_gap: Space between rows, in pixels.
            padding: Padding around the content.
            main_alignment: Horizontal alignment of the grid: 'start', 'center' or
                'end'.
            run_alignment: Vertical alignment of the grid: 'start', 'center' or
                'end'.
            item_alignment: Where a child sits in its cell: one value for both
                axes, or a ``(horizontal, vertical)`` pair of 'start', 'center'
                or 'end'. A child fills its cell on an axis by its own
                ``width`` / ``height`` of ``"wt"``.
            width: UniformFlow width.
            height: UniformFlow height.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(width=width, height=height, padding=padding, key=key)
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
        self._row_tracks: List[Tuple[float, float]] = []
        self._column_tracks: List[Tuple[float, float]] = []

    @property
    def row_tracks(self) -> List[Tuple[float, float]]:
        """Each row's ``(offset, length)`` from the last layout, relative to the flow; empty before one."""
        return list(self._row_tracks)

    @property
    def column_tracks(self) -> List[Tuple[float, float]]:
        """Each column's ``(offset, length)`` from the last layout, relative to the flow; empty before one."""
        return list(self._column_tracks)

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
        item_alignment: AlignValue = "start",
        width: SizingLike = None,
        height: SizingLike = None,
        key: Optional[str] = None,
    ) -> "UniformFlow":
        """Create a UniformFlow whose children are built from *items*.

        Args:
            items: Source data: a collection, or an observable of one -- the
                children then follow its changes.
            builder: Called as ``builder(item, index)`` for each item; returns
                the item's widget.
            columns: Number of columns. Takes precedence over *max_column_width*.
            max_column_width: Widest a column may get, in pixels; as many columns
                as fit the available width are used. With neither this nor
                *columns*, every child sits in one row.
            aspect_ratio: Cell width divided by cell height; sets a minimum cell
                height from the column width.
            main_gap: Space between columns, in pixels.
            cross_gap: Space between rows, in pixels.
            padding: Padding around the content.
            main_alignment: Horizontal alignment of the grid: 'start', 'center' or
                'end'.
            run_alignment: Vertical alignment of the grid: 'start', 'center' or
                'end'.
            item_alignment: Where a child sits in its cell: one value for both
                axes, or a ``(horizontal, vertical)`` pair of 'start', 'center'
                or 'end'. A child fills its cell on an axis by its own
                ``width`` / ``height`` of ``"wt"``.
            width: UniformFlow width.
            height: UniformFlow height.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
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
            key=key,
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
        return ("start", "start")

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

        outer_max_w: Optional[int] = None if max_width is None else int(max_width)
        if self.width_sizing.kind == "fixed":
            fixed_w = int(self.width_sizing.value)
            outer_max_w = fixed_w if outer_max_w is None else min(fixed_w, outer_max_w)
        inner_max_w: Optional[int] = None
        if outer_max_w is not None:
            inner_max_w = max(0, outer_max_w - int(pad[0]) - int(pad[2]))

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
            pref_w, _ = measure_preferred_size(child, max_width=col_limit)
            max_w = max(max_w, max(0, pref_w))
            max_h = max(max_h, self._contributed_height(child, col_limit))

        # If we have a constrained column width, use it for aspect ratio and size calculation
        # This matches layout() logic where columns expand to fill available width
        if col_limit is not None and col_limit > 0:
            max_w = max(max_w, col_limit)

        if self.aspect_ratio and max_w > 0:
            max_h = max(max_h, self._height_from_aspect(max_w))

        content_w = cols * max_w + max(0, cols - 1) * self.main_gap
        content_h = rows * max_h + max(0, rows - 1) * self.cross_gap
        return (int(content_w), int(content_h))

    @staticmethod
    def _contributed_height(child: Widget, max_width: Optional[int]) -> int:
        """The height a child adds to its row: its fixed height, else its measured one."""
        dim = child.height_sizing
        if dim.kind == "fixed":
            return max(0, int(dim.value))
        _, pref_h = measure_preferred_size(child, max_width=max_width)
        return max(0, pref_h)

    @staticmethod
    def _resolve_sizing(dim, fallback: int) -> int:
        if dim.kind == "fixed":
            return int(dim.value)
        return fallback

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        children = expand_layout_children(self.children_snapshot())
        self._laid_out_children = children
        self._row_tracks = []
        self._column_tracks = []
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
        row_heights = self._share_spare_height(row_heights, children, cols, inner_h)

        content_w = sum(col_widths) + max(0, cols - 1) * self.main_gap
        content_h = sum(row_heights) + max(0, rows - 1) * self.cross_gap

        start_x = pad[0] + align_offset(inner_w, content_w, self.main_alignment)
        start_y = pad[1] + align_offset(inner_h, content_h, self.run_alignment)

        col_offsets = compute_prefix_offsets(col_widths, self.main_gap)
        row_offsets = compute_prefix_offsets(row_heights, self.cross_gap)
        self._row_tracks = [(float(start_y + row_offsets[r]), float(row_heights[r])) for r in range(rows)]
        self._column_tracks = [(float(start_x + col_offsets[c]), float(col_widths[c])) for c in range(cols)]

        for i, child in enumerate(children):
            r = i // cols
            c = i % cols

            cell_w = col_widths[c]
            cell_h = row_heights[r]

            cell_x = start_x + col_offsets[c]
            cell_y = start_y + row_offsets[r]

            pref_w, pref_h = measure_preferred_size(child, max_width=cell_w)
            child_w = self._resolve_cell_size(child.width_sizing, pref_w, cell_w)
            child_h = self._resolve_cell_size(child.height_sizing, pref_h, cell_h)

            align_x, align_y = self.item_alignment
            cell_x += align_offset(cell_w, child_w, align_x)
            cell_y += align_offset(cell_h, child_h, align_y)

            child.layout(child_w, child_h)
            child.set_layout_rect(int(cell_x), int(cell_y), int(child_w), int(child_h))

    @staticmethod
    def _resolve_cell_size(dim, pref: int, cell: int) -> int:
        if dim.kind == "weight":
            return max(0, cell)
        if dim.kind == "fixed":
            return min(max(0, int(dim.value)), max(0, cell))
        return min(max(0, pref), max(0, cell))

    @replay_safe
    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        paint_laid_out_children(self, canvas, x, y, width, height)

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
            row = min(idx // cols, rows - 1)
            if self.aspect_ratio and col_widths:
                tile_h = self._height_from_aspect(col_widths[col])
                heights[row] = max(heights[row], tile_h)
            else:
                heights[row] = max(heights[row], self._contributed_height(child, cw))
        if self.aspect_ratio and col_widths:
            default_h = self._height_from_aspect(col_widths[0])
            heights = [h if h > 0 else default_h for h in heights]
        return heights

    def _share_spare_height(self, heights: List[int], children: List[Widget], cols: int, inner_h: int) -> List[int]:
        """Rows whose every child has a weight height split the height the other rows leave."""
        if self.aspect_ratio:
            return heights
        weight_rows = [
            r
            for r in range(len(heights))
            if all(child.height_sizing.kind == "weight" for child in children[r * cols : (r + 1) * cols])
        ]
        spare = inner_h - sum(heights) - max(0, len(heights) - 1) * self.cross_gap
        if not weight_rows or spare <= 0:
            return heights
        share, rem = divmod(spare, len(weight_rows))
        shared = list(heights)
        for i, r in enumerate(weight_rows):
            shared[r] += share + (1 if i < rem else 0)
        return shared

    def _height_from_aspect(self, width: int) -> int:
        if not self.aspect_ratio or self.aspect_ratio <= 0:
            return max(0, width)
        return max(1, int(round(width / self.aspect_ratio)))
