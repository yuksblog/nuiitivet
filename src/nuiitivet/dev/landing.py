"""Where a resize drag lands: ``int``, ``"auto"`` or ``"wt"``.

A dragged size is a number of pixels, but the framework's size policy has three
spellings, and two of them name a size the layout computes rather than one the
human chose. So a drag that ends within a few pixels of the widget's intrinsic
size lands on ``"auto"``, one that ends where a weight would put it lands on
``"wt"``, and anything else is the rounded integer. The targets are measured
from the live tree, with the parent's own arithmetic, so what the ghost shows
is what the reload will give.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Optional

from nuiitivet._interaction.perception import ancestors
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.layout_utils import expand_layout_children
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import ComposableWidget
from nuiitivet.widgets.box import Box

from .source_edit import SNAP_BAND, Value

logger = logging.getLogger(__name__)

AXES = ("width", "height")


@dataclass(frozen=True)
class Landing:
    """One axis's resolved landing: the value to write and the pixels it gives."""

    value: Value
    pixels: int


def editable_axes(node: Any) -> dict[str, str]:
    """Which axes a corner drag may change on ``node``, mapped to the keyword each writes.

    Read off the constructor: a ``size`` parameter couples both axes to one
    keyword, ``width`` / ``height`` are taken as present, and ``**kwargs`` is
    trusted to pass both through. Empty when the widget exposes none of them.
    """
    try:
        params = inspect.signature(type(node)).parameters
    except (TypeError, ValueError):
        return {}
    if "size" in params:
        return {"width": "size", "height": "size"}
    passes_through = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    return {axis: axis for axis in AXES if axis in params or passes_through}


def declared(node: Any, axis: str) -> Optional[Value]:
    """The sizing ``node`` currently declares on ``axis``, as a landing value.

    ``None`` for a weight other than one, which no drag can land on.
    """
    sizing = getattr(node, f"{axis}_sizing", None)
    if not isinstance(sizing, Sizing):
        return None
    if sizing.kind == "fixed":
        return int(sizing.value)
    if sizing.kind == "auto":
        return "auto"
    return "wt" if sizing.value == 1.0 else None


def intrinsic_size(node: Any, *, max_width: Optional[int] = None, max_height: Optional[int] = None) -> tuple[int, int]:
    """Measure ``node`` as ``"auto"`` on both axes would.

    A widget's own measurement honours a fixed sizing, so the declared sizes
    are swapped for ``auto`` for the duration of one measurement and put back,
    with the measure cache dropped on both sides so neither reading leaks into
    the other. No layout notification is raised: nothing has changed.
    """
    saved = (node.__dict__.get("_width_sizing"), node.__dict__.get("_height_sizing"))
    node._width_sizing = Sizing.auto()
    node._height_sizing = Sizing.auto()
    node._measure_cache = None
    try:
        width, height = measure_preferred_size(node, max_width=max_width, max_height=max_height)
        return (int(width), int(height))
    finally:
        node._width_sizing, node._height_sizing = saved
        node._measure_cache = None


def layout_container(node: Any) -> tuple[Optional[Any], Any]:
    """The container that lays ``node`` out, and the child of it on ``node``'s path.

    Composable wrappers are transparent to layout, so the walk passes through
    them; any other container in between is unknown arithmetic and yields
    ``None``.
    """
    member = node
    for ancestor in ancestors(node):
        if isinstance(ancestor, (Column, Row, Stack, Container, Box)):
            return (ancestor, member)
        if not isinstance(ancestor, ComposableWidget):
            return (None, member)
        member = ancestor
    return (None, member)


def content_extent(container: Any) -> Optional[tuple[int, int]]:
    """The width and height ``container`` offers its children, from its last layout."""
    rect = getattr(container, "layout_rect", None)
    if rect is None:
        return None
    left, top, right, bottom = getattr(container, "padding", (0, 0, 0, 0))
    return (max(0, int(rect[2]) - left - right), max(0, int(rect[3]) - top - bottom))


def weight_target(node: Any, axis: str) -> Optional[int]:
    """The pixels ``"wt"`` would give ``node`` on ``axis``, or ``None`` when unknown.

    On a stack's axis, or a column's cross axis, a weight fills the content
    extent. On a column's or row's main axis it is a share of what the fixed
    and ``auto`` siblings leave over, computed by the container's own
    allocation so the answer matches the reload to the pixel.
    """
    container, member = layout_container(node)
    if container is None:
        return None
    extent = content_extent(container)
    if extent is None:
        return None
    width, height = extent
    main = isinstance(container, Column) and axis == "height" or isinstance(container, Row) and axis == "width"
    if not main:
        return width if axis == "width" else height
    children = expand_layout_children(container.children_snapshot())
    if member not in children:
        return None
    usable = (height if axis == "height" else width) - max(0, len(children) - 1) * max(0, int(container.gap))
    bases: list[int] = []
    weights: list[float] = []
    for child in children:
        if child is member:
            bases.append(0)
            weights.append(1.0)
            continue
        sizing = getattr(child, f"{axis}_sizing", None)
        if sizing is None or sizing.kind == "auto":
            measured = measure_preferred_size(child, max_width=width if axis == "height" else None)
            bases.append(max(0, int(measured[1] if axis == "height" else measured[0])))
            weights.append(0.0)
        elif sizing.kind == "fixed":
            bases.append(max(0, int(sizing.value)))
            weights.append(0.0)
        else:
            bases.append(0)
            weights.append(float(sizing.value) if sizing.value > 0 else 1.0)
    allocated = type(container)._allocate_main_sizes(bases, weights, max(0, usable))
    return int(allocated[children.index(member)])


def resolve(proposed: float, intrinsic: Optional[int], weight: Optional[int], *, snap: bool = True) -> Landing:
    """Turn a dragged size into the value to write and the pixels it will give.

    ``auto`` wins over ``wt`` when both bands cover the point: the intrinsic
    size is the one that keeps meaning something when the parent changes.
    """
    pixels = max(1, int(round(proposed)))
    if snap:
        if intrinsic is not None and abs(proposed - intrinsic) <= SNAP_BAND:
            return Landing("auto", intrinsic)
        if weight is not None and abs(proposed - weight) <= SNAP_BAND:
            return Landing("wt", weight)
    return Landing(pixels, pixels)


__all__ = [
    "AXES",
    "Landing",
    "content_extent",
    "declared",
    "editable_axes",
    "intrinsic_size",
    "layout_container",
    "resolve",
    "weight_target",
]
