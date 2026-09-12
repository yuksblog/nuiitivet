"""Where a body drag lands: a slot among the siblings of one container.

A dragged widget is a position in pixels, but a ``Column`` / ``Row`` / ``Flow``
/ ``UniformFlow`` orders its children by their place in a list, so a body drag
resolves to a slot -- the sibling gap the pointer is over, read from the rects
layout gave the siblings -- and the edit that lands it is one element moved in
the ``children`` list literal. What is written is never a coordinate.

Whether such an edit exists at all is the source's question
(:func:`.source_edit.plan_move`): the list literal that owns the order -- the
``children`` list, or the data a comprehension or a ``ForEach`` iterates --
must be found, and every laid-out child must map to one of its elements.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from nuiitivet._interaction.perception import ancestors, global_visual_rect
from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.layout_utils import expand_layout_children
from nuiitivet.layout.row import Row
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.widgeting.widget import ComposableWidget

from .source import construction_frame

logger = logging.getLogger(__name__)

Rect = tuple[float, float, float, float]

#: The containers whose children a body drag can reorder.
REORDERABLE = (Column, Row, Flow, UniformFlow)

# How far an insertion line at a list's edge sits outside the first or last
# child, in logical pixels, so it is not lost under the child's own outline.
_EDGE = 3.0


def container_of(node: Any) -> tuple[Optional[Any], Any]:
    """The reorderable container laying ``node`` out, and its direct child on ``node``'s path.

    Composable wrappers are transparent; any other container in between means
    ``node`` is not a child of a list a drag can reorder, and the answer is
    ``(None, member)``. A ``ForEach`` is transparent too, but its children are
    the ones layout places, so the member stays below it.
    """
    member = node
    for ancestor in ancestors(node):
        if isinstance(ancestor, REORDERABLE):
            return (ancestor, member)
        if isinstance(ancestor, ForEach):
            continue
        if not isinstance(ancestor, ComposableWidget):
            return (None, member)
        member = ancestor
    return (None, member)


def visible(node: Any) -> Any:
    """The widget the human sees for a laid-out child.

    ``node`` itself when a user call built it; otherwise -- a fragment a
    ``ForEach`` wraps each item in -- the sole descendant a user call did
    build, which is what a caption or a check should name.
    """
    while construction_frame(node) is None:
        child = getattr(node, "built_child", None)
        if child is None:
            children = list(node.children_snapshot()) if hasattr(node, "children_snapshot") else []
            if len(children) != 1:
                break
            child = children[0]
        node = child
    return node


def siblings(container: Any) -> list[Any]:
    """The children layout placed, in layout order."""
    return list(expand_layout_children(container.children_snapshot()))


def reorder_reading(container: Any, dx: float, dy: float) -> bool:
    """Whether a drag by ``(dx, dy)`` reads as a reorder in ``container``.

    Travel along a ``Column``'s or ``Row``'s main axis is a reorder and travel
    across it is not: the cross axis is alignment's, and deciding by the
    dominant axis at release is what keeps the two gestures apart. A wrapping
    flow has no per-child cross reading, so every travel in it is a reorder.
    """
    if isinstance(container, Column):
        return abs(dy) >= abs(dx)
    if isinstance(container, Row):
        return abs(dx) >= abs(dy)
    return True


def slot_at(container: Any, children: list[Any], member: Any, x: float, y: float) -> int:
    """The slot the pointer is over: how many other siblings it has passed.

    A sibling is passed once the pointer crosses its midpoint on the main axis;
    in a wrapping flow, once its row is above the pointer, or its midpoint is
    behind the pointer on the pointer's own row.
    """
    passed = 0
    for child in children:
        if child is member:
            continue
        rect = global_visual_rect(child)
        if rect is None:
            continue
        if _before(container, rect, x, y):
            passed += 1
    return passed


def _before(container: Any, rect: Rect, x: float, y: float) -> bool:
    rx, ry, rw, rh = rect
    if isinstance(container, Column):
        return ry + rh / 2.0 < y
    if isinstance(container, Row):
        return rx + rw / 2.0 < x
    if ry + rh <= y:
        return True
    if ry > y:
        return False
    return rx + rw / 2.0 < x


def insertion_line(
    container: Any, children: list[Any], member: Any, slot: int, pointer: Optional[tuple[float, float]] = None
) -> Optional[Rect]:
    """The line the overlay draws for ``slot``, as a zero-thickness rect, or ``None``.

    It sits in the gap before the sibling that would follow the moved child,
    or past the last sibling, and spans the container's cross extent -- a
    sibling's own height in a wrapping flow, where a row is the extent that
    means anything. A slot at a flow's line break is one slot with two places
    to draw it, the end of one row and the start of the next; with ``pointer``
    given, the line is drawn on the row the pointer is on.
    """
    others = [child for child in children if child is not member]
    if not others:
        return None
    if slot < len(others):
        anchor, edge = global_visual_rect(others[slot]), -1
    else:
        anchor, edge = global_visual_rect(others[-1]), 1
    if anchor is None:
        return None
    if pointer is not None and 0 < slot < len(others) and not isinstance(container, (Column, Row)):
        previous = global_visual_rect(others[slot - 1])
        if previous is not None and _rows_apart(previous, anchor) and _nearer(pointer[1], previous, anchor):
            anchor, edge = previous, 1
    ax, ay, aw, ah = anchor
    extent = global_visual_rect(container) or anchor
    if isinstance(container, Column):
        span_x, span_w = extent[0], extent[2]
        line_y = ay - _EDGE if edge < 0 else ay + ah + _EDGE
        return (span_x, line_y, span_w, 0.0)
    line_x = ax - _EDGE if edge < 0 else ax + aw + _EDGE
    if isinstance(container, Row):
        return (line_x, extent[1], 0.0, extent[3])
    return (line_x, ay, 0.0, ah)


def _rows_apart(first: Rect, second: Rect) -> bool:
    """Whether two flow children sit on different rows: their vertical ranges do not overlap."""
    return first[1] + first[3] <= second[1] or second[1] + second[3] <= first[1]


def _nearer(y: float, first: Rect, second: Rect) -> bool:
    """Whether ``y`` is nearer the vertical centre of ``first`` than of ``second``."""
    return abs(y - (first[1] + first[3] / 2.0)) < abs(y - (second[1] + second[3] / 2.0))


__all__ = [
    "REORDERABLE",
    "container_of",
    "insertion_line",
    "reorder_reading",
    "siblings",
    "slot_at",
    "visible",
]
