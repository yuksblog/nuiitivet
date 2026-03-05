"""Overlay positioning helpers."""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from nuiitivet.layout.alignment import AlignmentLike, NINE_POINT_ALIGNMENTS, normalize_alignment
from nuiitivet.layout.measure import preferred_size as _measure_preferred_size
from nuiitivet.widgeting.widget import Widget


def _alignment_to_point(alignment: Tuple[str, str], width: int, height: int) -> Tuple[float, float]:
    """Compute the (x, y) point corresponding to *alignment* within a box of the given size."""
    ax, ay = alignment
    px = float(width) / 2.0 if ax == "center" else (float(width) if ax == "end" else 0.0)
    py = float(height) / 2.0 if ay == "center" else (float(height) if ay == "end" else 0.0)
    return (px, py)


class OverlayPosition:
    """Represents how an overlay entry is positioned within the overlay root."""

    def __init__(self, alignment: str, *, offset: Tuple[float, float] = (0.0, 0.0)) -> None:
        key = str(alignment).strip().lower().replace("_", "-")
        if key not in NINE_POINT_ALIGNMENTS:
            allowed = ", ".join(sorted(NINE_POINT_ALIGNMENTS))
            raise ValueError(f"Invalid alignment: {alignment!r}. Allowed: {allowed}")
        dx, dy = offset
        self.alignment_key = key
        self.offset = (float(dx), float(dy))

    @classmethod
    def alignment(
        cls,
        alignment: str,
        *,
        offset: Tuple[float, float] = (0.0, 0.0),
    ) -> "OverlayPosition":
        return cls(alignment, offset=offset)


class _AnchoredPositionedContent(Widget):
    """Full-screen widget that positions its child based on a lazily resolved anchor rect."""

    def __init__(
        self,
        child: Widget,
        *,
        rect_provider: Callable[[], Optional[Tuple[int, int, int, int]]],
        alignment: Tuple[str, str],
        anchor_point: Tuple[str, str],
        offset: Tuple[float, float],
    ) -> None:
        super().__init__(width="100%", height="100%")
        self._child = child
        self._rect_provider = rect_provider
        self._alignment = alignment
        self._anchor_point = anchor_point
        self._offset = offset
        self.add_child(child)

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        return (0, 0)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        child = self._child
        cw, ch = _measure_preferred_size(child)
        rect = self._rect_provider()
        if rect is None:
            child.layout(cw, ch)
            child.set_layout_rect(0, 0, cw, ch)
            return

        ax, ay, aw, ah = rect
        tx, ty = _alignment_to_point(self._alignment, aw, ah)
        cx, cy = _alignment_to_point(self._anchor_point, cw, ch)
        dx, dy = self._offset
        px = int(round(ax + tx - cx + dx))
        py = int(round(ay + ty - cy + dy))

        child.layout(cw, ch)
        child.set_layout_rect(px, py, cw, ch)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        child = self._child
        rect = child.layout_rect
        if rect is None:
            return
        cx, cy, cw, ch = rect
        child.paint(canvas, int(x) + cx, int(y) + cy, cw, ch)
        setter = getattr(child, "set_last_rect", None)
        if callable(setter):
            setter(int(x) + cx, int(y) + cy, cw, ch)

    def hit_test(self, x: int, y: int):
        hit = super().hit_test(x, y)
        if hit is self:
            return None
        return hit


class AnchoredOverlayPosition:
    """Positions overlay content anchored to a specific widget's screen rect.

    Unlike :class:`OverlayPosition`, which aligns content relative to the
    overlay root, this class lines up a reference point on the *content
    widget* with a reference point on the *anchor widget*.

    The anchor rect is resolved lazily via ``rect_provider`` so it always
    reflects the most recent layout/paint cycle.

    Usage::

        position = AnchoredOverlayPosition.anchored(
            rect_provider=my_box._rect_provider,
            alignment="bottom-left",
            anchor="top-left",
            offset=(0.0, 4.0),
        )
        overlay.show_modal(content, position=position, dismiss_on_outside_tap=True)
    """

    def __init__(
        self,
        rect_provider: Callable[[], Optional[Tuple[int, int, int, int]]],
        alignment: AlignmentLike,
        anchor: AlignmentLike,
        offset: Tuple[float, float],
    ) -> None:
        """
        Args:
            rect_provider: Callable returning the anchor widget's absolute screen
                rect ``(x, y, width, height)``, or ``None`` if not yet known.
            alignment: Reference point on the **anchor widget**.
            anchor: Reference point on the **content widget** to align to.
            offset: Additional ``(dx, dy)`` offset in screen pixels.
        """
        self._rect_provider = rect_provider
        self._alignment = normalize_alignment(alignment, default=("start", "end"))
        self._anchor_point = normalize_alignment(anchor, default=("start", "start"))
        self._offset = (float(offset[0]), float(offset[1]))

    @classmethod
    def anchored(
        cls,
        rect_provider: Callable[[], Optional[Tuple[int, int, int, int]]],
        alignment: AlignmentLike = "bottom-left",
        anchor: AlignmentLike = "top-left",
        offset: Tuple[float, float] = (0.0, 0.0),
    ) -> "AnchoredOverlayPosition":
        """Create an anchored overlay position.

        Args:
            rect_provider: Callable returning the anchor widget's absolute rect.
            alignment: Reference point on the anchor widget (default ``"bottom-left"``).
            anchor: Reference point on the content widget (default ``"top-left"``).
            offset: Additional ``(dx, dy)`` pixel offset.
        """
        return cls(rect_provider, alignment, anchor, offset)

    def make_position_content(self, content: Widget) -> Widget:
        """Wrap *content* in a full-screen container that positions it at the anchor.

        This method is called by :meth:`Overlay.show_modal` / :meth:`Overlay.show_modeless` when the position object
        exposes a ``make_position_content`` hook.

        Args:
            content: The overlay content widget to position.

        Returns:
            A widget that spans the full overlay root and places *content* at
            the computed anchor position.
        """
        return _AnchoredPositionedContent(
            content,
            rect_provider=self._rect_provider,
            alignment=self._alignment,
            anchor_point=self._anchor_point,
            offset=self._offset,
        )
