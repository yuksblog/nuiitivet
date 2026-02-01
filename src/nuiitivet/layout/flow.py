"""Flow layout: arrange children in a wrapping flow."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from .gap import normalize_gap
from .layout_utils import expand_layout_children
from .metrics import align_offset
from .for_each import ForEach, ItemsLike, BuilderFn
from .measure import preferred_size as measure_preferred_size


class Flow(Widget):
    """Layout children in rows that wrap.

    Arranges children in a horizontal run, wrapping to a new line when the line
    runs out of space.
    """

    def __init__(
        self,
        children: Optional[Sequence[Widget]] = None,
        *,
        main_gap: int = 0,
        cross_gap: int = 0,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        main_alignment: str = "start",
        run_alignment: str = "start",
        cross_alignment: str = "start",
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        super().__init__(width=width, height=height, padding=padding)
        if children:
            for child in children:
                self.add_child(child)

        self.main_gap = normalize_gap(main_gap)
        self.cross_gap = normalize_gap(cross_gap)
        self.main_alignment = main_alignment or "start"
        self.run_alignment = run_alignment or "start"
        self.cross_alignment = cross_alignment or "start"

    @classmethod
    def builder(
        cls,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        main_gap: int = 0,
        cross_gap: int = 0,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        main_alignment: str = "start",
        run_alignment: str = "start",
        cross_alignment: str = "start",
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> "Flow":
        """Create a Flow that materializes children from items via ForEach."""

        provider = ForEach(items, builder)
        return cls(
            [provider],
            main_gap=main_gap,
            cross_gap=cross_gap,
            padding=padding,
            main_alignment=main_alignment,
            run_alignment=run_alignment,
            cross_alignment=cross_alignment,
            width=width,
            height=height,
        )

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

        width, height = self._preferred_size_flow(children, inner_max_w)

        width = self._resolve_sizing(self.width_sizing, width + pad[0] + pad[2])
        height = self._resolve_sizing(self.height_sizing, height + pad[1] + pad[3])

        if max_width is not None and self.width_sizing.kind != "fixed":
            width = min(width, int(max_width))
        if max_height is not None and self.height_sizing.kind != "fixed":
            height = min(height, int(max_height))

        return (int(width), int(height))

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

    def _layout_flow(self, children: List[Widget], x: int, y: int, w: int, h: int) -> None:
        # Simple flow layout implementation
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
        # Calculate total content height for run_alignment
        total_content_h = sum(r[2] for r in rows) + max(0, len(rows) - 1) * self.cross_gap
        start_y = y + align_offset(h, total_content_h, self.run_alignment)

        current_y = start_y
        for row_items, row_w, row_h in rows:
            # Calculate row start x based on main_alignment
            start_x = x + align_offset(w, row_w, self.main_alignment)
            current_x = start_x

            for child, cw, ch in row_items:
                # Apply item alignment within the row height using cross_alignment
                child_y = current_y + align_offset(row_h, ch, self.cross_alignment)

                child.layout(cw, ch)
                child.set_layout_rect(int(current_x), int(child_y), int(cw), int(ch))

                current_x += cw + self.main_gap

            current_y += row_h + self.cross_gap
