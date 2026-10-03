"""Layout-related utility helpers.

Moved out from `utils.py` to separate layout concerns.
"""

import logging
import math
from typing import Any, List, Sequence, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia import local_clip_bounds

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from ..widgeting.widget import Widget


_logger = logging.getLogger(__name__)


def expand_layout_children(children: Sequence["Widget"]) -> List["Widget"]:
    """Replace each layout provider in ``children`` with the children it provides.

    A widget that implements ``provide_layout_children`` (a ``ForEach`` behind
    ``Row.builder(...)``) is never laid out itself: its provided children take
    its place, and a provider with nothing to provide leaves no child behind.
    """

    materialized: List["Widget"] = []
    for child in children:
        provider = getattr(child, "provide_layout_children", None)
        if callable(provider):
            try:
                materialized.extend(provider())
            except Exception:
                exception_once(_logger, "layout_utils_provide_layout_children_exc", "provide_layout_children failed")
            # The provider itself is not laid out, so we must clear its dirty flag
            # to ensure future invalidations propagate correctly.
            try:
                child.clear_needs_layout()
            except Exception:
                exception_once(_logger, "layout_utils_clear_needs_layout_exc", "clear_needs_layout failed")
            continue
        materialized.append(child)
    return materialized


def layout_child_if_needed(child: "Widget", width: int, height: int) -> None:
    """Run ``child.layout`` unless it would recompute an unchanged result.

    A clean child — nothing in its subtree called ``mark_needs_layout`` since
    its last pass — laid out again at the same size produces the same subtree
    geometry, because ``layout()`` is a pure function of the widget's state and
    its allocated size. Skipping the recursion
    makes re-arranging an unchanged sibling O(1). The caller still positions
    the child with ``set_layout_rect``; position is not an input to ``layout``.
    """

    rect = getattr(child, "layout_rect", None)
    if (
        rect is not None
        and not getattr(child, "needs_layout", True)
        and rect[2] == int(width)
        and rect[3] == int(height)
    ):
        return
    child.layout(width, height)


# How far outside the clip a child may sit and still be painted. Outsets are
# reported per widget, not per subtree, so a shadow or focus ring on a
# grandchild is invisible to the cull test; this band absorbs that.
_CULL_SLACK = 32


def paint_laid_out_children(container: Any, canvas: Any, x: int, y: int, width: int, height: int) -> None:
    """Paint a container's children at their layout rects.

    The child list is the one the container's last ``layout()`` kept, for as
    long as the container needs no layout: every change to its children marks
    it. A container painted without a layout builds the list here and lays
    itself out first.
    """

    inside_clip = container._paint_inside_clip
    if inside_clip:
        # The hint covers the paint it was set for and no later one.
        container._paint_inside_clip = False

    children = getattr(container, "_laid_out_children", None)
    if children is None or container.needs_layout:
        children = expand_layout_children(container.children_snapshot())
        if any(c.layout_rect is None for c in children):
            container.layout(width, height)

    if children:
        paint_children_at_layout_rects(children, canvas, x, y, inside_clip=inside_clip)


def paint_children_at_layout_rects(
    children: Sequence["Widget"], canvas: Any, x: int, y: int, *, inside_clip: bool = False
) -> None:
    """Paint each laid-out child at ``(x, y)`` plus its layout rect.

    A child whose visual bounds (layout rect plus ``paint_outsets``) end more
    than a small slack outside the canvas clip is not painted: the clip would
    discard every pixel, but only after the whole subtree had run its paint
    code. Its ``last_rect`` is still recorded so paint state stays consistent
    with what the parent placed. A child that draws outside its allocated rect
    must therefore report that through ``paint_outsets``. With no readable
    clip -- no canvas, or a stand-in -- every child is painted.

    A child that lies wholly inside the clip is told so, and a container that
    is told passes ``inside_clip``: nothing below it can be culled, so the clip
    is not read and no child is tested. Painting a child that the clip would
    have discarded is slower and never wrong, so a hint that is missing or out
    of date costs time and no pixel.
    """

    if inside_clip:
        for child in children:
            rect = child.layout_rect
            if rect is None:
                continue
            rel_x, rel_y, w, h = rect
            abs_x = x + rel_x
            abs_y = y + rel_y
            child.set_last_rect(abs_x, abs_y, w, h)
            child._paint_inside_clip = True
            child.paint(canvas, abs_x, abs_y, w, h)
        return

    clip = local_clip_bounds(canvas)
    if clip is None:
        clip_left = clip_top = -math.inf
        clip_right = clip_bottom = math.inf
        # Unknown clip: no child can be shown to lie inside it.
        in_left = in_top = math.inf
        in_right = in_bottom = -math.inf
    else:
        in_left, in_top, in_right, in_bottom = clip
        clip_left = in_left - _CULL_SLACK
        clip_top = in_top - _CULL_SLACK
        clip_right = in_right + _CULL_SLACK
        clip_bottom = in_bottom + _CULL_SLACK

    for child in children:
        rect = child.layout_rect
        if rect is None:
            continue

        rel_x, rel_y, w, h = rect
        abs_x = x + rel_x
        abs_y = y + rel_y

        child.set_last_rect(abs_x, abs_y, w, h)

        if abs_x >= clip_right or abs_y >= clip_bottom or abs_x + w <= clip_left or abs_y + h <= clip_top:
            try:
                out_l, out_t, out_r, out_b = child.paint_outsets()
            except Exception:
                exception_once(_logger, "layout_utils_paint_outsets_exc", "paint_outsets failed")
                out_l = out_t = out_r = out_b = 0
            if (
                abs_x - out_l >= clip_right
                or abs_y - out_t >= clip_bottom
                or abs_x + w + out_r <= clip_left
                or abs_y + h + out_b <= clip_top
            ):
                continue
        elif abs_x >= in_left and abs_y >= in_top and abs_x + w <= in_right and abs_y + h <= in_bottom:
            child._paint_inside_clip = True

        child.paint(canvas, abs_x, abs_y, w, h)
