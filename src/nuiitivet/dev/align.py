"""Where a body drag that stays put lands: an alignment name per axis.

A drag that keeps the widget's place in its container -- its own slot, its
own cell, a container with no order -- moves it within the box the container
aligns it in, and on each axis that box has three positions layout can give:
``start``, ``center`` and ``end``. The proposed rect snaps to the nearest, and
what is written is the container's own alignment keyword, so every child the
container aligns moves with it; the ghost shows each one where the new value
puts it. A ``CrossAligned`` the human wrote is theirs, and a drag on its child
rewrites that value instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Union

from nuiitivet._interaction.perception import global_visual_rect
from nuiitivet.layout.alignment import NINE_POINT_ALIGNMENTS, normalize_alignment
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.widgets.box import Box

from .reorder import siblings, visible

Rect = tuple[float, float, float, float]
Alignment = dict[str, str]
Spelled = Union[str, tuple[str, str]]

_NINE_POINT = {normalize_alignment(name, default=("start", "start")): name for name in NINE_POINT_ALIGNMENTS}


@dataclass(frozen=True)
class Target:
    """What an alignment drag writes.

    ``host`` is the widget whose call carries the keyword -- the container,
    or the ``CrossAligned`` / ``GridItem`` wrapping the dragged child --
    ``keyword`` and ``position`` where the value is written on that call, and
    ``axes`` the axes (``"x"`` / ``"y"``) the value aligns.
    """

    host: Any
    keyword: str
    position: Optional[int]
    axes: tuple[str, ...]

    @property
    def container_level(self) -> bool:
        """Whether every child of the host moves, rather than one wrapped child."""
        return not isinstance(self.host, (CrossAligned, GridItem, Container, Box))


def target(container: Any, member: Any) -> Optional[Target]:
    """The alignment a drag on ``member`` inside ``container`` writes, or ``None`` where there is none."""
    if isinstance(container, Grid):
        return Target(member, "alignment", None, ("x", "y")) if isinstance(member, GridItem) else None
    if isinstance(container, (Column, Row)):
        axis = "x" if isinstance(container, Column) else "y"
        if isinstance(member, CrossAligned):
            return Target(member, "alignment", 1, (axis,))
        return Target(container, "cross_alignment", None, (axis,))
    if isinstance(container, Flow):
        return Target(container, "cross_alignment", None, ("y",))
    if isinstance(container, UniformFlow):
        return Target(container, "item_alignment", None, ("x", "y"))
    if isinstance(container, (Stack, Container, Box)):
        return Target(container, "alignment", None, ("x", "y"))
    return None


def current(target: Target) -> Alignment:
    """The alignment the host applies now, per axis."""
    host = target.host
    if isinstance(host, CrossAligned):
        return {target.axes[0]: str(host.cross_align)}
    if isinstance(host, (Column, Row, Flow)):
        return {target.axes[0]: str(host.cross_alignment)}
    if isinstance(host, UniformFlow):
        return {"x": host.item_alignment[0], "y": host.item_alignment[1]}
    if isinstance(host, Stack):
        return {"x": host.alignment[0], "y": host.alignment[1]}
    pair = normalize_alignment(host.alignment, default=("start", "start"))
    return {"x": pair[0], "y": pair[1]}


def aligned(container: Any, member: Any) -> Any:
    """The widget the alignment moves: a ``GridItem``'s child, else the member itself."""
    if isinstance(container, Grid) and isinstance(member, GridItem):
        children = siblings(member)
        return visible(children[0]) if len(children) == 1 else member
    return member


def box(container: Any, member: Any) -> Optional[Rect]:
    """The global box ``container`` aligns ``member`` in, or ``None`` before layout.

    A container's content box; in a ``Column`` or ``Row`` only the cross
    extent matters, so the other axis is the child's own; in a flow the
    child's row, in a uniform flow its cell, in a grid the item's inner box.
    """
    if isinstance(container, Grid):
        return _content_box(member)
    if isinstance(container, (Stack, Container, Box)):
        return _content_box(container)
    child = global_visual_rect(member)
    if child is None:
        return None
    if isinstance(container, Column):
        content = _content_box(container)
        return (content[0], child[1], content[2], child[3]) if content else None
    if isinstance(container, Row):
        content = _content_box(container)
        return (child[0], content[1], child[2], content[3]) if content else None
    if isinstance(container, Flow):
        return _row_box(container, member, child)
    if isinstance(container, UniformFlow):
        return _cell_box(container, member)
    return None


def _content_box(container: Any) -> Optional[Rect]:
    rect = global_visual_rect(container)
    if rect is None:
        return None
    left, top, right, bottom = getattr(container, "padding", (0, 0, 0, 0))
    return (rect[0] + left, rect[1] + top, max(0.0, rect[2] - left - right), max(0.0, rect[3] - top - bottom))


def _row_box(flow: Any, member: Any, child: Rect) -> Rect:
    """The child's row in a wrapping flow: the union of the vertical extents of the children sharing it."""
    top, bottom = child[1], child[1] + child[3]
    for other in siblings(flow):
        rect = global_visual_rect(other)
        if rect is None or rect[1] + rect[3] <= top or rect[1] >= bottom:
            continue
        top, bottom = min(top, rect[1]), max(bottom, rect[1] + rect[3])
    return (child[0], top, child[2], bottom - top)


def _cell_box(flow: Any, member: Any) -> Optional[Rect]:
    rect = global_visual_rect(flow)
    children = siblings(flow)
    rows, columns = flow.row_tracks, flow.column_tracks
    if rect is None or member not in children or not rows or not columns:
        return None
    index = children.index(member)
    row, column = rows[index // len(columns)], columns[index % len(columns)]
    return (rect[0] + column[0], rect[1] + row[0], column[1], row[1])


def fills(child: Any, box: Rect, axis: str) -> bool:
    """Whether ``child`` already fills ``box`` on ``axis``, leaving nothing to align."""
    sizing = getattr(child, "width_sizing" if axis == "x" else "height_sizing", None)
    if sizing is not None and sizing.kind == "weight":
        return True
    rect = global_visual_rect(child)
    if rect is None:
        return True
    size, extent = (rect[2], box[2]) if axis == "x" else (rect[3], box[3])
    return size >= extent - 1.0


def snap(box: Rect, rect: Rect, delta: tuple[float, float], axes: tuple[str, ...]) -> Alignment:
    """The nearest alignment per axis to ``rect`` moved by ``delta`` within ``box``."""
    found: Alignment = {}
    for axis in axes:
        i = 0 if axis == "x" else 1
        proposed = rect[i] + delta[i]
        extent, size = box[i + 2], rect[i + 2]
        candidates = {name: box[i] + _offset(extent, size, name) for name in ("start", "center", "end")}
        found[axis] = min(candidates, key=lambda name: abs(candidates[name] - proposed))
    return found


def placed(box: Rect, rect: Rect, alignment: Mapping[str, str]) -> Rect:
    """``rect`` repositioned in ``box`` by ``alignment``, on the axes it names."""
    x = box[0] + _offset(box[2], rect[2], alignment["x"]) if "x" in alignment else rect[0]
    y = box[1] + _offset(box[3], rect[3], alignment["y"]) if "y" in alignment else rect[1]
    return (x, y, rect[2], rect[3])


def _offset(extent: float, size: float, name: str) -> float:
    if name == "center":
        return max(0.0, (extent - size) / 2.0)
    if name == "end":
        return max(0.0, extent - size)
    return 0.0


def moved(target: Target, container: Any, member: Any, alignment: Mapping[str, str]) -> list[tuple[Any, Rect]]:
    """Every widget the new alignment moves, with the rect it moves to.

    All of the container's children for a container-level value, less those
    with a ``CrossAligned`` of their own and those that fill the axis; only the
    dragged child otherwise.
    """
    members = siblings(container) if target.container_level else [member]
    found = []
    for each in members:
        if each is not member and getattr(each, "cross_align", None):
            continue
        child = aligned(container, each)
        extent, rect = box(container, each), global_visual_rect(child)
        if extent is None or rect is None:
            continue
        axes = {axis: name for axis, name in alignment.items() if not fills(child, extent, axis)}
        new = placed(extent, rect, axes)
        if new != rect:
            found.append((child, new))
    return found


def spell(target: Target, written: Optional[Spelled], value: Alignment) -> Spelled:
    """The value to write: a token for one axis; a nine-point name, a token, or a pair for two.

    The pair keeps the axes the drag left alone. A tuple stays a tuple, a
    single token stays one when both axes agree, and ``stretch`` -- which no
    nine-point name spells -- forces a tuple.
    """
    merged = {**current(target), **value}
    if len(target.axes) == 1:
        return merged[target.axes[0]]
    pair = (merged["x"], merged["y"])
    if isinstance(written, tuple) or "stretch" in pair:
        return pair
    if pair[0] == pair[1] and isinstance(written, str) and written not in NINE_POINT_ALIGNMENTS:
        return pair[0]
    return _NINE_POINT.get(pair, pair)


def describe(spelled: Spelled) -> str:
    """``spelled`` as a caption: ``center``, ``bottom-right`` or ``end, stretch``."""
    return spelled if isinstance(spelled, str) else ", ".join(spelled)


__all__ = [
    "Target",
    "aligned",
    "box",
    "current",
    "describe",
    "fills",
    "moved",
    "placed",
    "snap",
    "spell",
    "target",
]
