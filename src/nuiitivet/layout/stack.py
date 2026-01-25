"""Stack layout: arrange children on top of each other."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union

from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from .alignment import AlignmentLike, normalize_alignment
from .layout_utils import expand_layout_children
from .for_each import ForEach, ItemsLike, BuilderFn
from .measure import preferred_size as measure_preferred_size


class Stack(Widget):
    """Layout children on top of each other.

    Parameters
    - children: List of widgets to stack.
    - alignment: How to align children within the stack.
    """

    def __init__(
        self,
        children: Sequence[Widget],
        alignment: AlignmentLike = "top-left",
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ) -> None:
        super().__init__(width=width, height=height, padding=padding)
        for c in children:
            self.add_child(c)
        self.alignment = normalize_alignment(alignment, default=("start", "start"))

    @classmethod
    def builder(
        cls,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        alignment: AlignmentLike = "center",
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ) -> "Stack":
        """Create a Stack that materializes children from items via ForEach."""

        provider = ForEach(items, builder)
        return cls(
            children=[provider],
            alignment=alignment,
            width=width,
            height=height,
            padding=padding,
        )

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        children = expand_layout_children(self.children_snapshot())
        max_w = 0
        max_h = 0

        l, t, r, b = self.padding
        inner_max_w: Optional[int] = None
        inner_max_h: Optional[int] = None
        if max_width is not None:
            inner_max_w = max(0, int(max_width) - int(l) - int(r))
        elif self.width_sizing.kind == "fixed":
            inner_max_w = max(0, int(self.width_sizing.value) - int(l) - int(r))
        if max_height is not None:
            inner_max_h = max(0, int(max_height) - int(t) - int(b))
        elif self.height_sizing.kind == "fixed":
            inner_max_h = max(0, int(self.height_sizing.value) - int(t) - int(b))

        for child in children:
            w, h = measure_preferred_size(child, max_width=inner_max_w, max_height=inner_max_h)
            if int(w) > max_w:
                max_w = int(w)
            if int(h) > max_h:
                max_h = int(h)

        content_width = max_w
        content_height = max_h

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

        l, t, r, b = self.padding

        content_w = max(0, width - l - r)
        content_h = max(0, height - t - b)

        # Alignment
        ax, ay = self.alignment

        def get_pos(align: str, parent_size: int, child_size: int) -> int:
            if align == "center":
                return (parent_size - child_size) // 2
            elif align == "end":
                return parent_size - child_size
            return 0  # start

        for child in children:
            cw, ch = measure_preferred_size(child, max_width=content_w, max_height=content_h)

            target_w = cw
            target_h = ch

            # If child has percentage sizing (flex),
            # resolve it against stack size
            if hasattr(child, "width_sizing") and child.width_sizing.kind == "flex":
                target_w = int(content_w * (child.width_sizing.value / 100.0))

            if hasattr(child, "height_sizing") and child.height_sizing.kind == "flex":
                target_h = int(content_h * (child.height_sizing.value / 100.0))

            # Calculate position based on alignment
            x = get_pos(ax, content_w, target_w)
            y = get_pos(ay, content_h, target_h)

            child.layout(target_w, target_h)
            child.set_layout_rect(l + x, t + y, target_w, target_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        children = expand_layout_children(self.children_snapshot())
        for child in children:
            rect = child.layout_rect
            if rect is None:
                continue

            rx, ry, rw, rh = rect
            child.paint(canvas, x + rx, y + ry, rw, rh)
