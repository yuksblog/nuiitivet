"""Where a spacing drag lands: one side of a ``padding``, or a ``gap``, as an int on the 4dp grid.

The widget under the pointer, or the selection, carries a padding handle
on each outer edge and one handle in each gap between its children,
outlined: something to take hold of, beside the corner brackets that
resize. Under the pointer a handle fills, with every handle that moves along
with it: what a drag will move. How many move is the shape that will be
written: every side for an int, the pair for an ``(h, v)`` pair, the side
alone for a four-tuple; a click on a handle turns the shape to the next.
The handle is the only grab zone, so the
spacing region itself stays the body drag's of whatever child sits there,
and a handle at value 0 is still there to take hold of. The content's edge
is the zero: a padding handle pulled outward from it grows the padding, a
gap handle pushed along the axis grows the gap, and the band between the
content and the handle is the value. The band is drawn the way layout will
answer: out of the content on an axis the widget sizes to its content, in
from the outer edge on one it does not. The travel is rounded to the grid
unless the human asks for the pixel.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Optional

from nuiitivet._interaction.perception import global_visual_rect
from nuiitivet.layout.metrics import normalize_padding

from .landing import intrinsic_size
from .reorder import main_axis, siblings
from .source_edit import SNAP_BAND, Spacing

logger = logging.getLogger(__name__)

Rect = tuple[float, float, float, float]
Sides = tuple[int, int, int, int]

#: The padding sides in the order a four-tuple spells them.
SIDES = ("left", "top", "right", "bottom")
#: The increment a drag snaps to: MD3 lays spacing out on a 4dp grid.
GRID = 4
#: A handle's long and short side, in logical pixels.
LENGTH = 24.0
THICKNESS = 6.0
# Slack around a handle within which a press takes hold of it.
_GRAB = 3.0


@dataclass(frozen=True)
class Handle:
    """One grab zone on a selected container.

    Attributes:
        keyword: ``"padding"`` or ``"gap"``.
        side: For padding, the side held; for a gap, the container's main axis, ``"width"`` or ``"height"``.
        index: For a gap, the child before it; ``0`` for padding.
        rect: The handle's pill.
        filled: Whether the pill is drawn filled: it moves with the handle under the pointer or in hand.
    """

    keyword: str
    side: str
    index: int
    rect: Rect
    filled: bool = False

    def moves_with(self, other: "Handle", count: int) -> bool:
        """Whether this handle moves when ``other`` is dragged under a shape of ``count`` handles.

        A gap is one value, so every gap handle moves with any of them.
        """
        if self.keyword != other.keyword:
            return False
        return self.keyword == "gap" or self.side in fellows(other.side, count)


def editable(node: Any) -> dict[str, str]:
    """Which spacing keywords a handle may write on ``node``, read off its constructor.

    ``padding`` and ``gap`` are taken as present when the constructor names
    them. Empty when it names neither.
    """
    try:
        params = inspect.signature(type(node)).parameters
    except (TypeError, ValueError):
        return {}
    return {keyword: keyword for keyword in ("padding", "gap") if keyword in params}


def sides_of(node: Any) -> Sides:
    """``node``'s padding as ``(left, top, right, bottom)``, from the live widget."""
    return every_side(getattr(node, "padding", 0))


def every_side(value: Any) -> Sides:
    """A padding in any of its shapes as ``(left, top, right, bottom)``."""
    left, top, right, bottom = normalize_padding(value)
    return (int(left), int(top), int(right), int(bottom))


def gap_of(node: Any) -> int:
    """``node``'s gap, from the live widget."""
    return int(getattr(node, "gap", 0) or 0)


def content_rect(rect: Rect, sides: Sides) -> Rect:
    """``rect`` inset by ``sides``, never thinner than nothing."""
    x, y, w, h = rect
    left, top, right, bottom = sides
    return (x + left, y + top, max(0.0, w - left - right), max(0.0, h - top - bottom))


def shape_of(written: Optional[Spacing]) -> int:
    """How many padding handles the written padding asks for: one for an int or none, two for a pair, four."""
    return len(written) if isinstance(written, tuple) else 1


def next_shape(count: int) -> int:
    """The shape a click on a padding handle turns ``count`` into: one, two, four, and round again."""
    return {1: 2, 2: 4}.get(count, 1)


def fellows(side: str, count: int) -> tuple[str, ...]:
    """The sides that move with ``side`` under a shape of ``count`` handles.

    One handle moves every side, two move the pair the side belongs to,
    four move the side alone.
    """
    if count == 1:
        return SIDES
    if count == 2:
        return ("left", "right") if side in ("left", "right") else ("top", "bottom")
    return (side,)


def handles(node: Any, count: int = 4, held: Optional[tuple[Handle, int]] = None) -> list[Handle]:
    """Every handle on ``node``: one per padding side on its outer edges, one per gap between its children.

    All are outlined. With ``held``, a handle and a value, every handle that
    moves with it under a shape of ``count`` handles sits where the value
    puts it: the padding sides that move together, or every gap.
    """
    rect = global_visual_rect(node)
    keywords = editable(node)
    if rect is None or not keywords:
        return []
    found: list[Handle] = []
    if "padding" in keywords:
        sides = sides_of(node)
        riding = dict(zip(SIDES, sides))
        if held is not None and held[0].keyword == "padding":
            riding.update((fellow, held[1]) for fellow in fellows(held[0].side, count) if grows(node, fellow))
        proposed = tuple(riding[side] for side in SIDES)
        found.extend(_padding_handle(rect, sides, side, proposed) for side in SIDES)
    axis = main_axis(node) if "gap" in keywords else None
    if axis is not None:
        value = held[1] if held is not None and held[0].keyword == "gap" else None
        found.extend(handle for handle, _band in _gaps(node, rect, axis, value))
    return found


def _gaps(node: Any, rect: Rect, axis: str, value: Optional[int]) -> list[tuple[Handle, Rect]]:
    """Every gap of ``node`` along ``axis`` with its band: as laid out, or ``value`` wide, later children moved on."""
    gap = gap_of(node)
    # The handles line up on the content's centre line, the same line the
    # padding handles across the axis sit on, whatever width each child has.
    cx, cy, cw, ch = content_rect(rect, sides_of(node))
    line = cx + cw / 2.0 if axis == "height" else cy + ch / 2.0
    found: list[tuple[Handle, Rect]] = []
    rects = [global_visual_rect(child) for child in siblings(node)]
    for index, (first, second) in enumerate(zip(rects, rects[1:])):
        if first is None or second is None:
            continue
        if value is None:
            found.append((_gap_handle(axis, index, first, _gap_between(axis, first, second), line), rect))
            continue
        shift = (value - gap) * index
        x, y, w, h = first
        moved_first = (x + shift, y, w, h) if axis == "width" else (x, y + shift, w, h)
        found.append((_gap_handle(axis, index, moved_first, value, line), _gap_band(axis, rect, moved_first, value)))
    return found


def grows(node: Any, side: str) -> bool:
    """Whether a padding on ``side`` grows ``node`` outward, or eats into its content.

    Measured, not guessed: an ``"auto"`` axis laid out at its own intrinsic
    size grows with its padding. A fixed or weighted axis, or an ``"auto"``
    one the parent stretched -- the root filling its window -- keeps its
    extent, and the content's edge moves in.
    """
    axis = "width" if side in ("left", "right") else "height"
    sizing = getattr(node, f"{axis}_sizing", None)
    rect = global_visual_rect(node)
    if getattr(sizing, "kind", None) != "auto" or rect is None:
        return False
    try:
        natural = intrinsic_size(node)[0 if axis == "width" else 1]
    except Exception:
        logger.debug("spacing: measuring the intrinsic size failed", exc_info=True)
        return False
    return abs((rect[2] if axis == "width" else rect[3]) - natural) <= SNAP_BAND


def moved(node: Any, handle: Handle, value: int, count: int = 4) -> Optional[tuple[Handle, list[Rect]]]:
    """``handle`` where ``value`` puts it, and the bands it then spans, the held side's first, or ``None``.

    A padding handle spans one band per side that moves with it. On an axis
    that grows, a band grows out of the content's edge and the handle rides
    on its far edge. On one that does not, the band grows in from the outer
    edge and the handle stays on it.
    """
    rect = global_visual_rect(node)
    if rect is None:
        return None
    if handle.keyword == "padding":
        sides = sides_of(node)
        bands = [_proposed_band(node, rect, sides, side, value) for side in _held_first(handle.side, count)]
        riding = handles(node, count, (handle, value))
        return (next(h for h in riding if h.side == handle.side), bands)
    gaps = _gaps(node, rect, handle.side, value)
    held = next((pair for pair in gaps if pair[0].index == handle.index), None)
    if held is None:
        return None
    return (held[0], [held[1], *(band for other, band in gaps if other.index != handle.index)])


def _held_first(side: str, count: int) -> tuple[str, ...]:
    """The sides moving with ``side``, ``side`` itself first."""
    return (side, *(other for other in fellows(side, count) if other != side))


def _proposed_band(node: Any, rect: Rect, sides: Sides, side: str, value: int) -> Rect:
    """The band ``side`` takes at ``value``, out of the content or in from the edge as the axis answers."""
    if grows(node, side):
        return _padding_band(rect, sides, side, value)
    return _band_inward(rect, side, value)


def _padding_handle(rect: Rect, sides: Sides, side: str, proposed: tuple[int, ...]) -> Handle:
    """The handle of ``side``: on the content's edge pushed out by the ``proposed`` padding, mid-edge."""
    cx, cy, cw, ch = content_rect(rect, sides)
    at = proposed[SIDES.index(side)]
    centre = {
        "left": (cx - at, cy + ch / 2.0),
        "top": (cx + cw / 2.0, cy - at),
        "right": (cx + cw + at, cy + ch / 2.0),
        "bottom": (cx + cw / 2.0, cy + ch + at),
    }[side]
    return Handle("padding", side, 0, _pill(centre, "width" if side in ("top", "bottom") else "height"))


def _padding_band(rect: Rect, sides: Sides, side: str, value: int) -> Rect:
    """The band ``value`` thick outward from the content's edge on ``side``."""
    cx, cy, cw, ch = content_rect(rect, sides)
    x, y, w, h = rect
    return {
        "left": (cx - value, y, value, h),
        "top": (x, cy - value, w, value),
        "right": (cx + cw, y, value, h),
        "bottom": (x, cy + ch, w, value),
    }[side]


def _band_inward(rect: Rect, side: str, value: int) -> Rect:
    """The band ``value`` thick inward from the outer edge on ``side``."""
    x, y, w, h = rect
    return {
        "left": (x, y, value, h),
        "top": (x, y, w, value),
        "right": (x + w - value, y, value, h),
        "bottom": (x, y + h - value, w, value),
    }[side]


def _gap_between(axis: str, first: Rect, second: Rect) -> int:
    """The gap layout left between two children along ``axis``."""
    if axis == "height":
        return int(round(second[1] - first[1] - first[3]))
    return int(round(second[0] - first[0] - first[2]))


def _gap_handle(axis: str, index: int, first: Rect, value: int, line: float) -> Handle:
    """The handle of the gap after the child at ``first``: centred in a gap ``value`` wide, on ``line`` across it."""
    if axis == "height":
        centre = (line, first[1] + first[3] + value / 2.0)
    else:
        centre = (first[0] + first[2] + value / 2.0, line)
    return Handle("gap", axis, index, _pill(centre, "width" if axis == "height" else "height"))


def _gap_band(axis: str, rect: Rect, first: Rect, value: int) -> Rect:
    """The gap ``value`` wide after the child at ``first``, across the container."""
    x, y, w, h = rect
    if axis == "height":
        return (x, first[1] + first[3], w, float(value))
    return (first[0] + first[2], y, float(value), h)


def handle_at(node: Any, x: float, y: float, count: int = 4) -> Optional[Handle]:
    """The handle of ``node`` under the point, or ``None``."""
    for handle in handles(node, count):
        hx, hy, hw, hh = handle.rect
        if hx - _GRAB <= x <= hx + hw + _GRAB and hy - _GRAB <= y <= hy + hh + _GRAB:
            return handle
    return None


def region(node: Any, handle: Handle, count: int = 4) -> list[Rect]:
    """The spacing ``handle`` changes, as it stands: a band per side moving with it, or the gap after its child."""
    rect = global_visual_rect(node)
    if rect is None:
        return []
    if handle.keyword == "padding":
        sides = sides_of(node)
        return [_padding_band(rect, sides, side, sides[SIDES.index(side)]) for side in fellows(handle.side, count)]
    children = siblings(node)
    if handle.index + 1 >= len(children):
        return []
    first, second = global_visual_rect(children[handle.index]), global_visual_rect(children[handle.index + 1])
    if first is None or second is None:
        return []
    return [_gap_band(handle.side, rect, first, max(0, _gap_between(handle.side, first, second)))]


def landing(handle: Handle, base: int, dx: float, dy: float, *, snap: bool) -> int:
    """The value the held side or gap lands on after a travel of ``(dx, dy)`` from ``base``.

    A side grows as the pointer moves away from the content; a gap as the
    pointer moves along the axis. Never below zero; on the grid when ``snap``.
    """
    if handle.keyword == "padding":
        delta = {"left": -dx, "top": -dy, "right": dx, "bottom": dy}[handle.side]
    else:
        delta = dy if handle.side == "height" else dx
    value = max(0, int(round(base + delta)))
    return int(round(value / GRID)) * GRID if snap else value


def respelled(sides: Sides, side: str, value: int, count: int) -> Spacing:
    """The padding to write once ``side`` is ``value``, in the shape ``count`` handles stand for.

    One handle writes one int, every side at ``value``. Two write a pair,
    the held side's pair at ``value`` and the other pair as the left or top
    side has it. Four write every side, the held one at ``value``.
    """
    if count == 1:
        return value
    if count == 2:
        horizontal, vertical = sides[0], sides[1]
        return (value, vertical) if side in ("left", "right") else (horizontal, value)
    moved = list(sides)
    moved[SIDES.index(side)] = value
    return tuple(moved)


def _pill(centre: tuple[float, float], along: str) -> Rect:
    """A handle's rect centred on ``centre``, its length along ``along`` -- ``"width"`` or ``"height"``."""
    cx, cy = centre
    if along == "width":
        return (cx - LENGTH / 2.0, cy - THICKNESS / 2.0, LENGTH, THICKNESS)
    return (cx - THICKNESS / 2.0, cy - LENGTH / 2.0, THICKNESS, LENGTH)


__all__ = [
    "GRID",
    "Handle",
    "SIDES",
    "content_rect",
    "editable",
    "every_side",
    "fellows",
    "gap_of",
    "grows",
    "handle_at",
    "handles",
    "landing",
    "moved",
    "next_shape",
    "region",
    "respelled",
    "shape_of",
    "sides_of",
]
