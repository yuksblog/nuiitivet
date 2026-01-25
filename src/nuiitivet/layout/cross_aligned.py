from __future__ import annotations

import logging
from typing import Optional, Tuple

from nuiitivet.common.logging_once import exception_once

from ..widgeting.widget import Widget
from ..widgeting.widget_children import ChildContainerMixin
from .measure import preferred_size as measure_preferred_size


_logger = logging.getLogger(__name__)


class CrossAligned(Widget):
    """Layout wrapper that overrides cross-axis alignment in Row/Column.

    This sets `cross_align` metadata on the wrapper. Row/Column may read
    this to override their `cross_alignment` for this child only.
    """

    def __init__(
        self,
        child: Optional[Widget],
        alignment: str,
    ) -> None:
        super().__init__(
            width=child.width_sizing if child is not None else None,
            height=child.height_sizing if child is not None else None,
            padding=0,
            max_children=1,
            overflow_policy="replace_last",
        )
        self.cross_align = str(alignment)
        if child is not None:
            self.add_child(child)

    def add_child(self, w: "Widget") -> None:
        ChildContainerMixin.add_child(self, w)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        if not self.children:
            return (0, 0)
        return measure_preferred_size(self.children[0], max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        if not self.children:
            return
        child = self.children[0]
        child.layout(width, height)
        child.set_layout_rect(0, 0, width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        if not self.children:
            return

        child = self.children[0]
        if child.layout_rect is None:
            self.layout(width, height)

        rect = child.layout_rect
        if rect is None:
            abs_x, abs_y, child_w, child_h = x, y, width, height
        else:
            rel_x, rel_y, child_w, child_h = rect
            abs_x = x + int(rel_x)
            abs_y = y + int(rel_y)

        try:
            child.set_last_rect(abs_x, abs_y, child_w, child_h)
            child.paint(canvas, abs_x, abs_y, child_w, child_h)
        except Exception:
            exception_once(_logger, "cross_aligned_child_paint_exc", "CrossAligned child paint failed")

    def paint_outsets(self) -> Tuple[int, int, int, int]:
        if not self.children:
            return super().paint_outsets()
        try:
            return self.children[0].paint_outsets()
        except Exception:
            exception_once(_logger, "cross_aligned_child_paint_outsets_exc", "CrossAligned child paint_outsets failed")
            return super().paint_outsets()


__all__ = ["CrossAligned"]
