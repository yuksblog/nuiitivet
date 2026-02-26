from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from nuiitivet.layout.alignment import AlignmentLike, normalize_alignment
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget


def _alignment_to_point(alignment: tuple[str, str], width: int, height: int) -> tuple[float, float]:
    ax, ay = alignment

    if ax == "center":
        px = float(width) / 2.0
    elif ax == "end":
        px = float(width)
    else:
        px = 0.0

    if ay == "center":
        py = float(height) / 2.0
    elif ay == "end":
        py = float(height)
    else:
        py = 0.0

    return (px, py)


class StickBox(Widget):
    """A wrapper that overlays a sticker widget onto a base widget."""

    def __init__(
        self,
        child: Widget,
        sticker: Widget,
        *,
        alignment: AlignmentLike = "top-right",
        anchor: AlignmentLike = "center",
        offset: tuple[float, float] = (0.0, 0.0),
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        super().__init__(width=width, height=height, max_children=2, overflow_policy="replace_last")
        self._target_alignment = normalize_alignment(alignment, default=("end", "start"))
        self._sticker_anchor = normalize_alignment(anchor, default=("center", "center"))
        self._offset = (float(offset[0]), float(offset[1]))
        self._main_child = child
        self._sticker_child = sticker

        self.add_child(child)
        self.add_child(sticker)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        return measure_preferred_size(self._main_child, max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)

        self._main_child.layout(width, height)
        self._main_child.set_layout_rect(0, 0, width, height)

        sticker_w, sticker_h = measure_preferred_size(self._sticker_child)
        self._sticker_child.layout(sticker_w, sticker_h)

        tx, ty = _alignment_to_point(self._target_alignment, width, height)
        ax, ay = _alignment_to_point(self._sticker_anchor, sticker_w, sticker_h)
        dx, dy = self._offset

        px = int(round(tx - ax + dx))
        py = int(round(ty - ay + dy))
        self._sticker_child.set_layout_rect(px, py, sticker_w, sticker_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)

        if self._main_child.layout_rect is None or self._sticker_child.layout_rect is None:
            self.layout(width, height)

        main_rect = self._main_child.layout_rect
        sticker_rect = self._sticker_child.layout_rect
        if main_rect is None or sticker_rect is None:
            return

        mx, my, mw, mh = main_rect
        sx, sy, sw, sh = sticker_rect

        self._main_child.paint(canvas, x + mx, y + my, mw, mh)
        self._sticker_child.paint(canvas, x + sx, y + sy, sw, sh)

    def hit_test(self, x: int, y: int):
        main_hit = self._main_child.hit_test(x, y)
        if main_hit is not None:
            return main_hit
        sticker_hit = self._sticker_child.hit_test(x, y)
        if sticker_hit is not None:
            return sticker_hit
        return super().hit_test(x, y)


@dataclass(slots=True)
class StickModifier(ModifierElement):
    """Attach a sticker widget onto the modified widget."""

    badge: Widget
    alignment: AlignmentLike = "top-right"
    anchor: AlignmentLike = "center"
    offset: tuple[float, float] = (0.0, 0.0)

    def apply(self, widget: Widget) -> Widget:
        return StickBox(
            widget,
            self.badge,
            alignment=self.alignment,
            anchor=self.anchor,
            offset=self.offset,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def stick(
    badge: Widget,
    *,
    alignment: AlignmentLike = "top-right",
    anchor: AlignmentLike = "center",
    offset: tuple[float, float] = (0.0, 0.0),
) -> StickModifier:
    """Return a modifier that overlays a badge widget on top of a target widget.

    Args:
        badge: Overlay badge widget.
        alignment: Anchor point on the target widget.
        anchor: Anchor point on the badge widget.
        offset: Additional (dx, dy) offset in local coordinates.
    """
    return StickModifier(badge=badge, alignment=alignment, anchor=anchor, offset=offset)
