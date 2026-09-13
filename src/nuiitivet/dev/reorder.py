"""Where a body drag lands: a slot among the children of one container, or a grid cell.

A dragged widget is a position in pixels, but a ``Column`` / ``Row`` / ``Flow``
/ ``UniformFlow`` orders its children by their place in a list, so a body drag
resolves to a slot -- the sibling gap the pointer is over, read from the rects
layout gave the children -- and the edit that lands it is one element moved in
a ``children`` list literal: the widget's own container's when the pointer is
over it, another container's when it is over that. A ``Grid`` places its
children by cell, not by order, so over a grid the drag resolves to the cell
under the pointer, read from the tracks layout computed. What is written is
never a coordinate.

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
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.layout_utils import expand_layout_children
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.widgeting.widget import ComposableWidget
from nuiitivet.widgets.box import ModifierBox

from .gesture import pick
from .source import construction_frame

logger = logging.getLogger(__name__)

Rect = tuple[float, float, float, float]
Cell = tuple[int, int]

#: The containers that order their children, where a body drag lands in a slot.
REORDERABLE = (Column, Row, Flow, UniformFlow)
#: The containers a body drag can land in: the ordered ones, and a grid's cells.
DESTINATIONS = REORDERABLE + (Grid,)
#: The containers a body drag can start from: a ``Stack`` child cannot be
#: reordered, since stacked children share no axis, but it can leave.
SOURCES = DESTINATIONS + (Stack,)
#: Wrappers the container walk sees through: the list element is the wrapper,
#: since that is what the source names, and the widget inside is what the
#: human grabbed.
_TRANSPARENT = (ComposableWidget, ModifierBox, GridItem)

# How far an insertion line at a list's edge sits outside the first or last
# child, in logical pixels, so it is not lost under the child's own outline.
_EDGE = 3.0


def container_of(node: Any) -> tuple[Optional[Any], Any]:
    """The container a drag can move ``node`` out of, and its direct child on ``node``'s path.

    Composable wrappers, the box a ``.modifier()`` wraps a widget in and a
    ``GridItem`` are transparent, the member being the wrapper, since that is
    the list element; any other container in between means ``node`` is not a
    child of a list a drag can move, and the answer is ``(None, member)``. A
    ``ForEach`` is transparent too, but its children are the ones layout
    places, so the member stays below it.
    """
    member = node
    for ancestor in ancestors(node):
        if isinstance(ancestor, SOURCES):
            return (ancestor, member)
        if isinstance(ancestor, ForEach):
            continue
        if not isinstance(ancestor, _TRANSPARENT):
            return (None, member)
        member = ancestor
    return (None, member)


def destination_at(app: Any, x: float, y: float, exclude: Any, own: Any) -> Optional[Any]:
    """The container a drag over ``(x, y)`` would land in, or ``None``.

    The deepest container under the pointer that can take a child, looking
    past the dragged subtree -- ``exclude`` and everything under it -- since a
    widget cannot move into itself. The widget's ``own`` container ends the
    walk even when it cannot take a child (a ``Stack``): while the pointer is
    inside it, the reading is its own, not an ancestor's.
    """
    picked = pick(app, x, y)
    if picked is None:
        return None
    chain = [picked, *ancestors(picked)]
    if exclude in chain:
        chain = chain[chain.index(exclude) + 1 :]
    for node in chain:
        if node is own or isinstance(node, DESTINATIONS):
            return node
    return None


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


def inner(member: Any) -> Any:
    """The widget a list element stands for: a ``GridItem``'s child, else the element itself."""
    if isinstance(member, GridItem):
        children = list(member.children_snapshot())
        if len(children) == 1:
            return visible(children[0])
    return visible(member)


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
    return not isinstance(container, Stack)


def main_axis(container: Any) -> Optional[str]:
    """``"height"`` for a ``Column``, ``"width"`` for a ``Row``; ``None`` where no axis is main."""
    if isinstance(container, Column):
        return "height"
    if isinstance(container, Row):
        return "width"
    return None


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
    given, the line is drawn on the row the pointer is on. An empty
    container's one slot is drawn at the start of its content box.
    """
    others = [child for child in children if child is not member]
    if not others:
        return _empty_line(container)
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


def _empty_line(container: Any) -> Optional[Rect]:
    rect = global_visual_rect(container)
    if rect is None:
        return None
    left, top, right, bottom = getattr(container, "padding", (0, 0, 0, 0))
    x, y, w, h = rect[0] + left, rect[1] + top, max(0.0, rect[2] - left - right), max(0.0, rect[3] - top - bottom)
    if isinstance(container, Column):
        return (x, y + _EDGE, w, 0.0)
    return (x + _EDGE, y, 0.0, h)


def _rows_apart(first: Rect, second: Rect) -> bool:
    """Whether two flow children sit on different rows: their vertical ranges do not overlap."""
    return first[1] + first[3] <= second[1] or second[1] + second[3] <= first[1]


def _nearer(y: float, first: Rect, second: Rect) -> bool:
    """Whether ``y`` is nearer the vertical centre of ``first`` than of ``second``."""
    return abs(y - (first[1] + first[3] / 2.0)) < abs(y - (second[1] + second[3] / 2.0))


# --- grids ----------------------------------------------------------------


def cell_at(grid: Any, x: float, y: float) -> Optional[Cell]:
    """The ``(row, column)`` of ``grid`` under the pointer, or ``None`` over its padding.

    Read from the tracks layout computed; a pointer in the gap between two
    tracks belongs to the nearer one. Only tracks layout resolved exist: a
    cell beyond them would be one the grid has not drawn.
    """
    rect = global_visual_rect(grid)
    if rect is None:
        return None
    row = _track_at(grid.row_tracks, y - rect[1])
    column = _track_at(grid.column_tracks, x - rect[0])
    if row is None or column is None:
        return None
    return (row, column)


def _track_at(tracks: list[tuple[float, float]], v: float) -> Optional[int]:
    for index, (offset, length) in enumerate(tracks):
        if v < offset:
            if index == 0:
                return None
            previous_end = tracks[index - 1][0] + tracks[index - 1][1]
            return index - 1 if v - previous_end < offset - v else index
        if v < offset + length:
            return index
    return None


def cell_rect(grid: Any, row: int, column: int, row_span: int = 1, column_span: int = 1) -> Optional[Rect]:
    """The global rect of the cells from ``(row, column)`` spanning ``row_span`` × ``column_span``, or ``None``."""
    rect = global_visual_rect(grid)
    rows, columns = grid.row_tracks, grid.column_tracks
    if rect is None or row >= len(rows) or column >= len(columns):
        return None
    top, bottom = rows[row], rows[min(row + row_span, len(rows)) - 1]
    left, right = columns[column], columns[min(column + column_span, len(columns)) - 1]
    return (rect[0] + left[0], rect[1] + top[0], right[0] + right[1] - left[0], bottom[0] + bottom[1] - top[0])


def placement(grid: Any, member: Any) -> Optional[tuple[int, int, int, int]]:
    """Where ``member`` sits in ``grid`` as ``(row, column, row_span, column_span)``, or ``None``."""
    try:
        return grid.placement_of(member)
    except (TypeError, ValueError):
        return None


def occupants(grid: Any, cell: Cell, exclude: Any) -> list[Any]:
    """The children of ``grid`` other than ``exclude`` whose placement covers ``cell``."""
    found = []
    for child in siblings(grid):
        if child is exclude:
            continue
        placed = placement(grid, child)
        if placed is None:
            continue
        row, column, row_span, column_span = placed
        if row <= cell[0] < row + row_span and column <= cell[1] < column + column_span:
            found.append(child)
    return found


def area_at(grid: Any, cell: Cell) -> Optional[str]:
    """The name of the template area covering ``cell``, or ``None`` when the grid declares none."""
    areas = getattr(grid, "areas", None)
    if not areas or cell[0] >= len(areas) or cell[1] >= len(areas[cell[0]]):
        return None
    return str(areas[cell[0]][cell[1]])


__all__ = [
    "DESTINATIONS",
    "REORDERABLE",
    "SOURCES",
    "area_at",
    "cell_at",
    "cell_rect",
    "container_of",
    "destination_at",
    "inner",
    "insertion_line",
    "main_axis",
    "occupants",
    "placement",
    "reorder_reading",
    "siblings",
    "slot_at",
    "visible",
]
