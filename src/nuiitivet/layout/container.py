import logging
from typing import Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from ..widgeting.widget import Widget
from ..widgeting.widget_children import ChildContainerMixin
from ..rendering.sizing import SizingLike
from .alignment import normalize_alignment
from .layout_engine import LayoutEngine
from .measure import preferred_size as measure_preferred_size


_logger = logging.getLogger(__name__)


class Container(Widget):
    """Lightweight layout-only Container.

    This Container is a minimal single-child layout box. It intentionally
    does not perform background/shadow/border drawing or clipping.
    """

    def __init__(
        self,
        child: Optional[Widget] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        alignment: Union[str, Tuple[str, str]] = "start",
    ):
        """Initialize the Container.

        Args:
            child: The child widget to be placed inside the container.
            width: The preferred width of the container. Defaults to None (shrinkwrap).
            height: The preferred height of the container. Defaults to None (shrinkwrap).
            padding: Padding to apply around the child. Can be a single integer,
                a 2-tuple (horizontal, vertical), or a 4-tuple (left, top, right, bottom).
            alignment: How to align the child within the container. Defaults to "start".
                Can be a string (e.g., "center") or a tuple (horizontal, vertical).
        """
        super().__init__(
            width=width,
            height=height,
            padding=padding,
            max_children=1,
            overflow_policy="replace_last",
        )

        self._align = normalize_alignment(alignment, default=("start", "start"))

        # child management + layout engine
        if child is not None:
            self.add_child(child)
        self._layout = LayoutEngine(self)

    def add_child(self, w: "Widget"):
        """Keep at most one child; call ChildContainerMixin directly to bypass overrides."""
        ChildContainerMixin.add_child(self, w)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        child_max_w: Optional[int] = None
        child_max_h: Optional[int] = None

        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            child_max_w = int(w_dim.value)
        elif max_width is not None:
            child_max_w = int(max_width)

        if h_dim.kind == "fixed":
            child_max_h = int(h_dim.value)
        elif max_height is not None:
            child_max_h = int(max_height)

        if child_max_w is not None or child_max_h is not None:
            pad = self.padding
            # Container is lightweight and has no border; use Box if borders are needed.
            if child_max_w is not None:
                child_max_w = max(0, int(child_max_w) - int(pad[0]) - int(pad[2]))
            if child_max_h is not None:
                child_max_h = max(0, int(child_max_h) - int(pad[1]) - int(pad[3]))

        if len(self.children) == 0:
            inner_w, inner_h = 0, 0
        else:
            inner_w, inner_h = measure_preferred_size(self.children[0], max_width=child_max_w, max_height=child_max_h)

        layout_w, layout_h = self._layout.preferred_size(int(inner_w or 0), int(inner_h or 0))

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = int(layout_w)
            if max_width is not None:
                width = min(width, int(max_width))

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = int(layout_h)
            if max_height is not None:
                height = min(height, int(max_height))

        return (width, height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        if not self.children:
            return

        child = self.children[0]
        # Calculate layout relative to self (0, 0)
        ix, iy, iw, ih = self._layout.compute_inner_rect(0, 0, width, height)
        cx, cy, child_w, child_h = self._layout.resolve_child_geometry(child, ix, iy, iw, ih)

        child.layout(child_w, child_h)
        child.set_layout_rect(cx, cy, child_w, child_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        # Minimal paint: update last rect and delegate to child paint.
        self.set_last_rect(x, y, width, height)

        if len(self.children) == 0:
            return

        child = self.children[0]

        # Auto-layout fallback for tests or direct paint calls
        if child.layout_rect is None:
            self.layout(width, height)

        rect = child.layout_rect
        if rect:
            rel_x, rel_y, child_w, child_h = rect
            cx = x + rel_x
            cy = y + rel_y
        else:
            # Fallback if layout failed
            ix, iy, iw, ih = self._layout.compute_inner_rect(x, y, width, height)
            cx, cy, child_w, child_h = self._layout.resolve_child_geometry(child, ix, iy, iw, ih)

        # Container does not clip; child is painted as-is.
        try:
            child.set_last_rect(cx, cy, child_w, child_h)
            child.paint(canvas, cx, cy, child_w, child_h)
        except Exception:
            exception_once(_logger, "container_child_paint_exc", "Container child paint failed")
