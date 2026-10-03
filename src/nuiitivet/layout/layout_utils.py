"""Layout-related utility helpers.

Moved out from `utils.py` to separate layout concerns.
"""

import logging
import math
from typing import Any, List, Optional, Sequence, Tuple, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia import get_skia, local_clip_bounds
from nuiitivet.widgeting.paint_replay import REPLAY_HOOKS

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

    # A hint covers the paint it was set for and no later one.
    inside_clip = container._paint_inside_clip
    if inside_clip:
        container._paint_inside_clip = False
    scroll_content = container._paint_scroll_content
    if scroll_content:
        container._paint_scroll_content = False

    children = getattr(container, "_laid_out_children", None)
    if children is None or container.needs_layout:
        children = expand_layout_children(container.children_snapshot())
        if any(c.layout_rect is None for c in children):
            container.layout(width, height)

    if children:
        paint_children_at_layout_rects(
            children, canvas, x, y, inside_clip=inside_clip, scroll_content=scroll_content
        )


# Tests turn this off to compare a replayed frame against a direct paint.
_ROW_REPLAY = True

# A row that changed on more consecutive paints than this is painted directly:
# recording a row every frame costs more than not recording it.
_CHURN_LIMIT = 2

_replay_safe_types: dict[type, bool] = {}

# (matrix, scale_x, scale_y, translate_x, translate_y, clip_width, clip_height)
_Rows = Tuple[Any, float, float, float, float, float, float]


def _type_replay_safe(cls: type) -> bool:
    safe = _replay_safe_types.get(cls)
    if safe is None:
        safe = all(
            getattr(getattr(cls, name, None), "_replay_safe", False) for name in REPLAY_HOOKS if hasattr(cls, name)
        )
        _replay_safe_types[cls] = safe
    return safe


def _subtree_replay_safe(root: Any) -> bool:
    """Whether every widget in ``root``'s subtree declares its drawing safe to replay."""
    stack = [root]
    while stack:
        node = stack.pop()
        if not _type_replay_safe(type(node)):
            return False
        stack.extend(node.children_snapshot())
        built = getattr(node, "built_child", None)
        if built is not None:
            stack.append(built)
    return True


def _rows_of(canvas: Any, clip: Optional[Tuple[float, float, float, float]]) -> Optional[_Rows]:
    """Read what replaying rows on ``canvas`` needs, or ``None`` when it cannot replay."""
    if not _ROW_REPLAY or clip is None:
        return None
    read = getattr(canvas, "getTotalMatrix", None)
    if read is None or getattr(canvas, "drawPicture", None) is None:
        return None
    try:
        matrix = read()
        scale_x = matrix.getScaleX()
        # A stand-in canvas answers with something that is not a matrix of floats.
        if type(scale_x) is not float or matrix.getSkewX() != 0.0 or matrix.getSkewY() != 0.0:
            return None
        return (
            matrix,
            scale_x,
            matrix.getScaleY(),
            matrix.getTranslateX(),
            matrix.getTranslateY(),
            clip[2] - clip[0],
            clip[3] - clip[1],
        )
    except Exception:
        return None


def _paint_row(child: Any, canvas: Any, x: int, y: int, w: int, h: int, rows: _Rows) -> bool:
    """Draw a scroll row from its recording, recording it first when it changed.

    The canvas is not moved by a scroll viewport, so a row is recorded at the
    device position it had and replayed shifted by how far it has moved since.

    Returns:
        ``False`` when the row has to be painted directly: it holds a widget
        that is not declared safe to replay, it is larger than the viewport, or
        it changes on every frame.
    """
    matrix, scale_x, scale_y, translate_x, translate_y, clip_w, clip_h = rows
    device_x = scale_x * x + translate_x
    device_y = scale_y * y + translate_y
    key = (w, h, scale_x, scale_y)

    picture = child._replay_picture
    if child._replay_dirty:
        child._replay_misses += 1
        # Anything the paint below invalidates marks the row again.
        child._replay_dirty = False
        child._replay_skip = False
        picture = None
        if child._replay_misses > _CHURN_LIMIT:
            child._replay_picture = None
            return False
    else:
        child._replay_misses = 0
        if child._replay_skip:
            return False
        if picture is not None and child._replay_key == key:
            origin_x, origin_y = child._replay_origin
            canvas.save()
            canvas.resetMatrix()
            canvas.translate(device_x - origin_x, device_y - origin_y)
            canvas.drawPicture(picture)
            canvas.restore()
            return True

    child._replay_picture = None
    skia = get_skia(raise_if_missing=False)
    if skia is None or w > clip_w or h > clip_h or not _subtree_replay_safe(child):
        child._replay_skip = True
        return False

    try:
        out_l, out_t, out_r, out_b = child.paint_outsets()
    except Exception:
        exception_once(_logger, "layout_utils_paint_outsets_exc", "paint_outsets failed")
        out_l = out_t = out_r = out_b = 0
    x0 = scale_x * (x - out_l - _CULL_SLACK) + translate_x
    x1 = scale_x * (x + w + out_r + _CULL_SLACK) + translate_x
    y0 = scale_y * (y - out_t - _CULL_SLACK) + translate_y
    y1 = scale_y * (y + h + out_b + _CULL_SLACK) + translate_y
    recorder = skia.PictureRecorder()
    target = recorder.beginRecording(skia.Rect.MakeLTRB(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    # The recording carries the canvas matrix, so a widget that rasterises its
    # own cache at the device scale sees the scale it will be shown at.
    target.setMatrix(matrix)
    child._paint_inside_clip = True
    child.paint(target, x, y, w, h)
    picture = recorder.finishRecordingAsPicture()

    child._replay_picture = picture
    child._replay_origin = (device_x, device_y)
    child._replay_key = key
    canvas.save()
    canvas.resetMatrix()
    canvas.drawPicture(picture)
    canvas.restore()
    return True


def paint_children_at_layout_rects(
    children: Sequence["Widget"],
    canvas: Any,
    x: int,
    y: int,
    *,
    inside_clip: bool = False,
    scroll_content: bool = False,
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

    With ``scroll_content`` the children are the rows of a scroll viewport's
    content. A row is recorded when it enters the clip and replayed, shifted,
    while nothing at or below it has invalidated; a row that leaves the clip
    gives its recording up.
    """

    if inside_clip and not scroll_content:
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

    rows = _rows_of(canvas, clip) if scroll_content else None

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
                if rows is not None and child._replay_picture is not None:
                    child._replay_picture = None
                continue
        elif rows is not None:
            if _paint_row(child, canvas, abs_x, abs_y, w, h, rows):
                continue
        elif abs_x >= in_left and abs_y >= in_top and abs_x + w <= in_right and abs_y + h <= in_bottom:
            child._paint_inside_clip = True

        child.paint(canvas, abs_x, abs_y, w, h)
