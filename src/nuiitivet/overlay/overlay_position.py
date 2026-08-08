"""Overlay positioning.

:class:`OverlayPosition` is the single abstraction for "where does this overlay
content go". Instances are built through its named constructors, never by
calling the class directly:

===========================  ===========================================
Constructor                  Places content relative to
===========================  ===========================================
:meth:`~OverlayPosition.aligned`     the overlay root (the whole window)
:meth:`~OverlayPosition.anchored`    a widget's screen rect
:meth:`~OverlayPosition.at_point`    a screen point
:meth:`~OverlayPosition.at_pointer`  a :class:`PointerEvent`'s screen point
===========================  ===========================================

Every kind exposes the same :meth:`~OverlayPosition.make_position_content` hook,
so :meth:`Overlay.show` takes one position argument and never
branch on which kind they were handed.
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.layout.alignment import (
    AlignmentLike,
    NINE_POINT_ALIGNMENTS,
    alignment_to_point as _alignment_to_point,
    normalize_alignment,
)
from nuiitivet.layout.measure import preferred_size as _measure_preferred_size
from nuiitivet.widgeting.widget import Widget


class OverlayPosition:
    """Where overlay content is placed within the overlay root.

    Build one with :meth:`aligned`, :meth:`anchored`, :meth:`at_point` or
    :meth:`at_pointer`; this base class is not instantiated directly.
    """

    @staticmethod
    def aligned(
        alignment: str = "center",
        *,
        offset: Tuple[float, float] = (0.0, 0.0),
    ) -> "OverlayPosition":
        """Place content relative to the overlay root.

        Args:
            alignment: One of the nine-point placements (``"center"``,
                ``"bottom-center"``, ...) within the overlay root.
            offset: Additional ``(dx, dy)`` pixel offset.

        Raises:
            ValueError: If *alignment* is not a nine-point placement.
        """
        return _AlignedOverlayPosition(alignment, offset=offset)

    @staticmethod
    def anchored(
        rect_provider: Callable[[], Optional[Tuple[int, int, int, int]]],
        target_anchor: AlignmentLike = "bottom-left",
        content_anchor: AlignmentLike = "top-left",
        offset: Tuple[float, float] = (0.0, 0.0),
        *,
        clamp: bool = True,
    ) -> "OverlayPosition":
        """Place content relative to a widget's screen rect.

        ``content_anchor`` on the content is lined up with ``target_anchor`` on
        the anchor widget. The rect is resolved lazily on every layout pass, so
        the content follows the anchor as it moves.

        Args:
            rect_provider: Callable returning the anchor widget's absolute screen
                rect ``(x, y, width, height)``, or ``None`` if not yet known.
            target_anchor: Reference point on the anchor widget.
            content_anchor: Reference point on the content widget.
            offset: Additional ``(dx, dy)`` offset in screen pixels.
            clamp: Keep the content inside the viewport (default ``True``).
        """
        return _AnchoredOverlayPosition(
            rect_provider,
            target_anchor,
            content_anchor,
            offset,
            clamp=clamp,
        )

    @staticmethod
    def at_point(
        x: float,
        y: float,
        *,
        content_anchor: AlignmentLike = "top-left",
        offset: Tuple[float, float] = (0.0, 0.0),
        clamp: bool = True,
    ) -> "OverlayPosition":
        """Place content relative to a fixed screen point.

        A point has no extent, so there is no ``target_anchor`` to choose:
        ``content_anchor`` alone decides which corner of the content lands on
        ``(x, y)``.

        Args:
            x: Screen x coordinate.
            y: Screen y coordinate.
            content_anchor: Reference point on the content widget.
            offset: Additional ``(dx, dy)`` offset in screen pixels.
            clamp: Keep the content inside the viewport (default ``True``).
        """
        point = (int(round(x)), int(round(y)), 0, 0)
        return _AnchoredOverlayPosition(
            lambda: point,
            "top-left",
            content_anchor,
            offset,
            clamp=clamp,
        )

    @staticmethod
    def at_pointer(
        event: PointerEvent,
        *,
        content_anchor: AlignmentLike = "top-left",
        offset: Tuple[float, float] = (0.0, 0.0),
        clamp: bool = True,
    ) -> "OverlayPosition":
        """Place content at the screen point a pointer event occurred at.

        Prefer this over ``at_point(event.x, event.y)``: a ``PointerEvent``
        carries both screen (``x``/``y``) and widget-relative
        (``local_x``/``local_y``) coordinates, and only the screen pair is
        meaningful to an overlay. Passing the event lets this method pick.

        Args:
            event: The pointer event to place the content at.
            content_anchor: Reference point on the content widget.
            offset: Additional ``(dx, dy)`` offset in screen pixels.
            clamp: Keep the content inside the viewport (default ``True``).
        """
        return OverlayPosition.at_point(
            event.x,
            event.y,
            content_anchor=content_anchor,
            offset=offset,
            clamp=clamp,
        )

    def make_position_content(self, content: Widget) -> Widget:
        """Wrap *content* in a full-screen widget that places it.

        Called by :meth:`Overlay.show` for every position kind.

        Args:
            content: The overlay content widget to position.

        Returns:
            A widget spanning the overlay root that places *content*.
        """
        raise NotImplementedError


class _AlignedPositionedContent(Widget):
    """Full-screen widget that aligns its child within the overlay root."""

    def __init__(self, child: Widget, *, alignment: str, offset: Tuple[float, float]) -> None:
        super().__init__(width="100%", height="100%")
        self._child = child
        self._alignment = str(alignment)
        dx, dy = offset
        self._offset = (float(dx), float(dy))
        self.add_child(child)

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        # This widget expands; preferred size is irrelevant.
        return (0, 0)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)

        child = self._child
        cw, ch = child.preferred_size(max_width=width, max_height=height)
        target_w = int(cw)
        target_h = int(ch)

        # Flex is a weight, not a fraction of the parent. The overlay content is
        # the sole claimant on both axes, so a flex child fills the available
        # extent (see docs/design/SIZE_POLICY.md).
        if hasattr(child, "width_sizing") and child.width_sizing.kind == "flex":
            target_w = width
        if hasattr(child, "height_sizing") and child.height_sizing.kind == "flex":
            target_h = height

        ax, ay = normalize_alignment(self._alignment, default=("center", "center"))

        def get_pos(align: str, parent_size: int, child_size: int) -> int:
            if align == "center":
                return (parent_size - child_size) // 2
            if align == "end":
                return parent_size - child_size
            return 0

        dx, dy = self._offset
        x = int(get_pos(ax, width, target_w) + dx)
        y = int(get_pos(ay, height, target_h) + dy)

        child.layout(target_w, target_h)
        child.set_layout_rect(x, y, target_w, target_h)

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


class _AlignedOverlayPosition(OverlayPosition):
    """Positions content relative to the overlay root."""

    def __init__(self, alignment: str, *, offset: Tuple[float, float] = (0.0, 0.0)) -> None:
        key = str(alignment).strip().lower().replace("_", "-")
        if key not in NINE_POINT_ALIGNMENTS:
            allowed = ", ".join(sorted(NINE_POINT_ALIGNMENTS))
            raise ValueError(f"Invalid alignment: {alignment!r}. Allowed: {allowed}")
        dx, dy = offset
        self.alignment_key = key
        self.offset = (float(dx), float(dy))

    def make_position_content(self, content: Widget) -> Widget:
        """Wrap *content* so it is aligned within the overlay root."""
        return _AlignedPositionedContent(
            content,
            alignment=self.alignment_key,
            offset=self.offset,
        )


class _AnchoredPositionedContent(Widget):
    """Full-screen widget that positions its child based on a lazily resolved anchor rect."""

    def __init__(
        self,
        child: Widget,
        *,
        rect_provider: Callable[[], Optional[Tuple[int, int, int, int]]],
        target_anchor: Tuple[str, str],
        content_anchor: Tuple[str, str],
        offset: Tuple[float, float],
        clamp: bool,
    ) -> None:
        super().__init__(width="100%", height="100%")
        self._child = child
        self._rect_provider = rect_provider
        self._target_anchor = target_anchor
        self._content_anchor = content_anchor
        self._offset = offset
        self._clamp = clamp
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
        tx, ty = _alignment_to_point(self._target_anchor, aw, ah)
        cx, cy = _alignment_to_point(self._content_anchor, cw, ch)
        dx, dy = self._offset
        px = int(round(ax + tx - cx + dx))
        py = int(round(ay + ty - cy + dy))

        if self._clamp:
            # ``width``/``height`` are the overlay root's extent, i.e. the
            # viewport. Content larger than the viewport pins to the top-left so
            # its leading edge stays reachable rather than scrolling off.
            px = max(0, min(px, width - cw)) if cw <= width else 0
            py = max(0, min(py, height - ch)) if ch <= height else 0

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

    # No hit_test override needed: this is a transparent full-screen positioning
    # wrapper, so the ``auto`` default (defer to children) already passes hits
    # through to the positioned content and never catches on self. See #448.


class _AnchoredOverlayPosition(OverlayPosition):
    """Positions content relative to a lazily resolved anchor rect.

    A point-anchored position is the degenerate case: a zero-size rect at the
    point, which makes every ``target_anchor`` equivalent.
    """

    def __init__(
        self,
        rect_provider: Callable[[], Optional[Tuple[int, int, int, int]]],
        target_anchor: AlignmentLike,
        content_anchor: AlignmentLike,
        offset: Tuple[float, float],
        *,
        clamp: bool = True,
    ) -> None:
        self._rect_provider = rect_provider
        self._target_anchor = normalize_alignment(target_anchor, default=("start", "end"))
        self._content_anchor = normalize_alignment(content_anchor, default=("start", "start"))
        self._offset = (float(offset[0]), float(offset[1]))
        self._clamp = bool(clamp)

    def make_position_content(self, content: Widget) -> Widget:
        """Wrap *content* in a full-screen container that places it at the anchor."""
        return _AnchoredPositionedContent(
            content,
            rect_provider=self._rect_provider,
            target_anchor=self._target_anchor,
            content_anchor=self._content_anchor,
            offset=self._offset,
            clamp=self._clamp,
        )
