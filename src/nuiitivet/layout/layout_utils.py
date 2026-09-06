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
    """Expand any children that act as layout providers (e.g. ForEach).

    Widgets can implement ``provide_layout_children`` to return a list of
    widgets that should participate directly in the parent's layout. When
    present, the provider's own widget is skipped and the returned children are
    used instead. This enables declarative constructs such as Row.builder(...)
    where the ForEach provider does not paint but supplies multiple children to
    the Row.
    """

    materialized: List["Widget"] = []
    for child in children:
        provider = getattr(child, "provide_layout_children", None)
        if callable(provider):
            try:
                provided = provider()
            except Exception:
                exception_once(_logger, "layout_utils_provide_layout_children_exc", "provide_layout_children failed")
                provided = None
            if provided:
                materialized.extend(list(provided))
                # The provider itself is not laid out, so we must clear its dirty flag
                # to ensure future invalidations propagate correctly.
                try:
                    child.clear_needs_layout()
                except Exception:
                    exception_once(_logger, "layout_utils_clear_needs_layout_exc", "clear_needs_layout failed")
                # An empty provider misses this branch and is laid out as an ordinary
                # child, so drop the zero-area rect it was stamped with back then.
                try:
                    child.clear_layout_rect()
                except Exception:
                    exception_once(_logger, "layout_utils_clear_layout_rect_exc", "clear_layout_rect failed")
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


def paint_children_at_layout_rects(children: Sequence["Widget"], canvas: Any, x: int, y: int) -> None:
    """Paint each laid-out child at ``(x, y)`` plus its layout rect.

    A child whose visual bounds (layout rect plus ``paint_outsets``) end more
    than a small slack outside the canvas clip is not painted: the clip would
    discard every pixel, but only after the whole subtree had run its paint
    code. Its ``last_rect`` is still recorded so paint state stays consistent
    with what the parent placed. A child that draws outside its allocated rect
    must therefore report that through ``paint_outsets``. With no readable
    clip -- no canvas, or a stand-in -- every child is painted.
    """

    clip = local_clip_bounds(canvas)
    if clip is None:
        clip_left = clip_top = -math.inf
        clip_right = clip_bottom = math.inf
    else:
        clip_left, clip_top, clip_right, clip_bottom = clip
        clip_left -= _CULL_SLACK
        clip_top -= _CULL_SLACK
        clip_right += _CULL_SLACK
        clip_bottom += _CULL_SLACK

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

        child.paint(canvas, abs_x, abs_y, w, h)
