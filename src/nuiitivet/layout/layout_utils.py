"""What the containers share: a frame's layout and its deadline, a provider's children, painting at layout rects."""

import logging
import math
import weakref
from collections import deque
from time import perf_counter
from typing import Any, Deque, List, Optional, Sequence, Tuple, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia import get_skia, local_clip_bounds
from nuiitivet.widgeting.frame_clock import frame_interval, frame_started_at
from nuiitivet.widgeting.paint_replay import REPLAY_HOOKS

if TYPE_CHECKING:  # pragma: no cover
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
            # Nothing lays the provider out, so nothing else clears its flag.
            try:
                child.clear_needs_layout()
            except Exception:
                exception_once(_logger, "layout_utils_clear_needs_layout_exc", "clear_needs_layout failed")
            continue
        materialized.append(child)
    return materialized


# The share of a frame its layout may spend. The rest is left to paint.
LAYOUT_SHARE = 0.5

# The end of the frame's layout under way; ``None`` outside one.
_deadline: Optional[float] = None

# In the order the passes reached them: a parent before anything below it.
_pending: Deque["weakref.ref[Widget]"] = deque()


def layout_deadline() -> Optional[float]:
    """The moment the layout under way stops descending into children sized by their parent.

    ``None`` outside a frame's layout: a test, a headless render, a pass a
    widget runs on its own.
    """
    return _deadline


def layout_frame(root: "Widget", width: int, height: int, *, root_pass: bool) -> None:
    """Run a frame's layout: the root's pass, then the subtrees the frames before left pending.

    Inside a frame the two together stop after :data:`LAYOUT_SHARE` of a
    frame, counted from this call. Where no frame is under way, a test or a
    headless render, they run to the end.

    Args:
        root: The root of the tree.
        width: The width the root is laid out at.
        height: The height the root is laid out at.
        root_pass: Whether the root is laid out: it is dirty, or its size
            changed.
    """
    global _deadline
    outer = _deadline
    _deadline = perf_counter() + frame_interval() * LAYOUT_SHARE if frame_started_at() is not None else None
    try:
        try:
            if root_pass:
                root.layout(width, height)
                root.clear_needs_layout()
        finally:
            # A root whose layout raises on every frame must not keep them waiting.
            _layout_pending_subtrees()
    finally:
        _deadline = outer


def sized_by_parent(child: "Widget") -> bool:
    """Whether ``child``'s rect is its parent's to decide: each axis fixed or weighted, neither from its content."""
    return child.width_sizing.kind != "auto" and child.height_sizing.kind != "auto"


def layout_child_if_needed(child: "Widget", width: int, height: int, *, sized_by_parent: bool = False) -> None:
    """Lay ``child`` out, unless it is clean at this size or the layout has no time left.

    The caller positions the child with ``set_layout_rect`` in every case.

    Args:
        child: The child to lay out.
        width: The width the parent allocated.
        height: The height the parent allocated.
        sized_by_parent: The rect came from the parent, not from measuring the
            child. Past :func:`layout_deadline` such a child is left pending:
            it keeps the rect, nothing below it runs, it is painted as nothing,
            and the next frame lays it out.
    """

    rect = getattr(child, "layout_rect", None)
    if (
        rect is not None
        and not child._layout_pending
        and not getattr(child, "needs_layout", True)
        and rect[2] == int(width)
        and rect[3] == int(height)
    ):
        return
    if sized_by_parent:
        deadline = layout_deadline()
        if deadline is not None and perf_counter() >= deadline:
            _leave_pending(child)
            return
    if child._layout_pending:
        # Not left to ``layout()``: an override may not reach the kernel's.
        _end_pending(child)
    child.layout(width, height)


def _leave_pending(child: "Widget") -> None:
    if child._layout_pending:
        return
    child._layout_pending = True
    _pending.append(weakref.ref(child))


def _end_pending(child: "Widget") -> None:
    child._layout_pending = False
    # The pictures recorded while it was blank are stale.
    child._mark_replay_dirty()


def has_pending_layout(app: Any = None) -> bool:
    """Whether a child left pending by a frame's layout waits for the next frame.

    Args:
        app: The window to ask about: only the children mounted in it count.
            ``None`` counts every pending child.
    """
    for ref in _pending:
        child = ref()
        if child is not None and child._layout_pending and (app is None or child._app is app):
            return True
    return False


def _layout_pending_subtrees() -> None:
    """Lay the pending subtrees out, top-down, until the deadline of the layout under way."""
    while _pending and (_deadline is None or perf_counter() < _deadline):
        child = _pending.popleft()()
        if child is None or not child._layout_pending:
            continue
        _end_pending(child)
        rect = child.layout_rect
        if rect is None or child.parent is None:
            # It left the tree and no frame shows it. Dirty, so the pass that takes it back lays it out.
            child.mark_needs_layout()
            continue
        mark = len(_pending)
        try:
            child.layout(rect[2], rect[3])
        except Exception:
            exception_once(_logger, "layout_utils_pending_layout_exc", "A pending child's layout failed")
            continue
        # What this layout left pending goes first: a subtree fills whole before the next one starts.
        _pending.extendleft([_pending.pop() for _ in range(len(_pending) - mark)])


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

    A child left pending by the layout is painted as nothing. A child whose
    layout rect plus ``paint_outsets`` ends beyond the canvas clip and a small
    slack is not painted. Both still get their ``last_rect``. A child that
    draws outside its rect must report that through ``paint_outsets``. With no
    readable clip, no canvas or a stand-in, every child is painted.

    Args:
        children: The children to paint.
        canvas: The canvas to paint on.
        x: The left edge of the parent on the canvas.
        y: The top edge of the parent on the canvas.
        inside_clip: The parent lies wholly inside the clip. The clip is not
            read and no child is tested against it.
        scroll_content: The children are the rows of a scroll viewport's
            content. A row is recorded when it enters the clip and replayed,
            shifted, while nothing at or below it has invalidated. A row that
            leaves the clip gives its recording up.
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
            if child._layout_pending:
                continue
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
        if child._layout_pending:
            continue

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
