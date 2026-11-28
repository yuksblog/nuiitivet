"""What the containers share: a frame's layout and its deadline, a provider's children, painting at layout rects."""

import logging
import math
import weakref
from bisect import bisect_left, bisect_right
from collections import deque
from time import perf_counter
from typing import Any, Callable, Deque, List, Optional, Sequence, Tuple, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia import clip_rect, get_skia, local_clip_bounds
from nuiitivet.widgeting.frame_clock import frame_interval, frame_started_at
from nuiitivet.widgeting.paint_replay import REPLAY_HOOKS
from nuiitivet.widgeting.unlaid_child import warn_child_without_rect

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
            it keeps the rect, nothing below it runs, it is painted from its
            last layout, and the next frame lays it out.
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
            leave_pending(child)
            return
    if child._layout_pending:
        # Not left to ``layout()``: an override may not reach the kernel's.
        end_pending(child)
    _lay_out(child, width, height)


def _lay_out(child: "Widget", width: int, height: int) -> None:
    child.layout(width, height)
    child._laid_out_size = (int(width), int(height))


def leave_pending(child: "Widget") -> None:
    """Leave ``child`` pending: the next frame lays it out at its rect.

    Until then it is painted from its last layout. A widget whose own layout
    stopped at :func:`layout_deadline` with work left that shows calls this
    on itself.
    """
    if child._layout_pending:
        return
    child._layout_pending = True
    # The kernel's layout clears the flag and leaves the entry behind.
    if not any(ref() is child for ref in _pending):
        _pending.append(weakref.ref(child))


def end_pending(child: "Widget") -> None:
    """End ``child``'s pending state; its layout is the one painted from now on."""
    child._layout_pending = False
    # The pictures recorded while it showed its last layout are stale.
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
        end_pending(child)
        rect = child.layout_rect
        if rect is None or child.parent is None:
            # It left the tree and no frame shows it. Dirty, so the pass that takes it back lays it out.
            child.mark_needs_layout()
            continue
        mark = len(_pending)
        try:
            _lay_out(child, rect[2], rect[3])
        except Exception:
            exception_once(_logger, "layout_utils_pending_layout_exc", "A pending child's layout failed")
            continue
        # What this layout left pending goes first: a subtree fills whole before the next one starts.
        _pending.extendleft([_pending.pop() for _ in range(len(_pending) - mark)])


# How far outside the clip a child may sit and still be painted. Outsets are
# reported per widget, not per subtree, so a shadow or focus ring on a
# grandchild is invisible to the cull test; this band absorbs that.
_CULL_SLACK = 32


# Answers which of a container's laid-out children a rect reaches, as
# ``(start, stop)`` into the list. The rect is ``(left, top, right, bottom)``
# in the container's coordinates. Every child outside the span lies wholly
# beyond the rect.
Reach = Callable[[Sequence["Widget"], float, float, float, float], Tuple[int, int]]


def reach_down(children: Sequence["Widget"], left: float, top: float, right: float, bottom: float) -> Tuple[int, int]:
    """The span of ``children`` the rect reaches, for children laid out top to bottom without overlap."""
    try:
        start = bisect_right(children, top, key=_bottom_of)
        return (start, bisect_left(children, bottom, lo=start, key=_top_of))
    except TypeError:
        # A child with no rect.
        return (0, len(children))


def reach_across(
    children: Sequence["Widget"], left: float, top: float, right: float, bottom: float
) -> Tuple[int, int]:
    """The span of ``children`` the rect reaches, for children laid out left to right without overlap."""
    try:
        start = bisect_right(children, left, key=_right_of)
        return (start, bisect_left(children, right, lo=start, key=_left_of))
    except TypeError:
        return (0, len(children))


def _top_of(child: "Widget") -> int:
    return child.layout_rect[1]  # type: ignore[index]


def _bottom_of(child: "Widget") -> int:
    rect = child.layout_rect
    return rect[1] + rect[3]  # type: ignore[index]


def _left_of(child: "Widget") -> int:
    return child.layout_rect[0]  # type: ignore[index]


def _right_of(child: "Widget") -> int:
    rect = child.layout_rect
    return rect[0] + rect[2]  # type: ignore[index]


def paint_laid_out_children(container: Any, canvas: Any, x: int, y: int, *, reach: Optional[Reach] = None) -> None:
    """Paint a container's children at their layout rects.

    The child list is the one the container's last ``layout()`` kept, for as
    long as the container needs no layout: every change to its children marks
    it. A container that needs a layout builds the list here. A child with no
    rect is not painted.

    Args:
        container: The container whose children are painted.
        canvas: The canvas to paint on.
        x: The left edge of the container on the canvas.
        y: The top edge of the container on the canvas.
        reach: Answers which children the clip reaches, so that the paint
            visits those only. A child the paint stops visiting gives up its
            recordings and its ``last_rect``. ``None`` visits every child.
    """

    # A hint covers the paint it was set for and no later one.
    inside_clip = container._paint_inside_clip
    if inside_clip:
        container._paint_inside_clip = False

    children = getattr(container, "_laid_out_children", None)
    laid_out = children is not None and not container.needs_layout
    if not laid_out:
        children = expand_layout_children(container.children_snapshot())
    if not children:
        return

    if reach is None or inside_clip:
        if reach is not None:
            _leave_span(container, children, 0, len(children))
        paint_children_at_layout_rects(children, canvas, x, y, inside_clip=inside_clip)
        return

    clip = local_clip_bounds(canvas)
    start, stop = 0, len(children)
    if laid_out and clip is not None:
        out_l, out_t, out_r, out_b = _children_outsets(container, children)
        # A child on one side reaches in by its outset on the side facing the clip.
        start, stop = reach(
            children,
            clip[0] - x - _CULL_SLACK - out_r,
            clip[1] - y - _CULL_SLACK - out_b,
            clip[2] - x + _CULL_SLACK + out_l,
            clip[3] - y + _CULL_SLACK + out_t,
        )
    _leave_span(container, children, start, stop)
    if start > 0 or stop < len(children):
        children = children[start:stop]
    if children:
        _paint_culled(children, canvas, x, y, clip, _replay_of(canvas))


def _children_outsets(container: Any, children: List["Widget"]) -> Tuple[int, int, int, int]:
    """The largest outset of any of ``children`` on each side, kept until the list changes."""
    kept = container._children_outsets
    if kept is not None and kept[0] is children:
        return kept[1]
    left = top = right = bottom = 0
    for child in children:
        out_l, out_t, out_r, out_b = _outsets(child)
        left = max(left, out_l)
        top = max(top, out_t)
        right = max(right, out_r)
        bottom = max(bottom, out_b)
    outsets = (left, top, right, bottom)
    container._children_outsets = (children, outsets)
    return outsets


def _leave_span(container: Any, children: List["Widget"], start: int, stop: int) -> None:
    """Keep the span this paint visits; the children the last paint visited and this one skips leave."""
    last = container._painted_span
    container._painted_span = (children, start, stop)
    if last is None:
        return
    old, old_start, old_stop = last
    if old is children:
        for index in range(old_start, min(old_stop, start)):
            _leave(children[index])
        for index in range(max(old_start, stop), old_stop):
            _leave(children[index])
        return
    kept = {id(child) for child in children[start:stop]}
    for child in old[old_start:old_stop]:
        # A child moved to another container is that container's to paint.
        if id(child) not in kept and _held_by(container, child):
            _leave(child)


def _held_by(container: Any, child: "Widget") -> bool:
    """Whether ``child`` is ``container``'s, directly or through a provider."""
    parent = child._parent
    return parent is container or (parent is not None and parent._parent is container)


def _leave(child: "Widget") -> None:
    # Off the canvas, a last rect would say where the widget was before.
    _forget_pictures(child, last_rects=True)


# Tests turn this off to compare a replayed frame against a direct paint.
_REPLAY = True

# The device bounds of the recording under way, or ``None``. No recording
# starts inside one: it would hold the same widgets a second time.
_recording: Optional[Tuple[float, float, float, float]] = None

# Whether the recording under way left a widget out.
_recording_cut = False

# How many pending children are being painted from their last layout. Below
# one a paint clears no mark and records nothing: the layout still to come
# may change what it drew, and the marks must be there for the paint after it.
_stale_paints = 0

# A recording's canvas bounds: far enough that its clip is only what the widgets below set.
_FAR = 1.0e8

_replay_safe_types: dict[type, bool] = {}

# (matrix, scale_x, scale_y, translate_x, translate_y)
_Replay = Tuple[Any, float, float, float, float]


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


def _replay_of(canvas: Any) -> Optional[_Replay]:
    """Read what replaying children on ``canvas`` needs, or ``None`` when it cannot replay."""
    if not _REPLAY:
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
        scale_y = matrix.getScaleY()
        if scale_x == 0.0 or scale_y == 0.0:
            return None
        return (matrix, scale_x, scale_y, matrix.getTranslateX(), matrix.getTranslateY())
    except Exception:
        return None


def _forget_pictures(root: Any, *, last_rects: bool = False) -> None:
    """Give up the recordings in ``root``'s subtree, and with ``last_rects`` its last rects: it left the clip."""
    stack = [root]
    while stack:
        node = stack.pop()
        node._replay_picture = None
        # As before any paint: it is recorded when it comes back.
        node._replay_key = None
        if last_rects:
            node.clear_last_rect()
        stack.extend(node.children_snapshot())
        built = getattr(node, "built_child", None)
        if built is not None:
            stack.append(built)


def _outsets(child: Any) -> Tuple[int, int, int, int]:
    try:
        return child.paint_outsets()
    except Exception:
        exception_once(_logger, "layout_utils_paint_outsets_exc", "paint_outsets failed")
        return (0, 0, 0, 0)


def _outsets_outside(
    child: Any, x: int, y: int, w: int, h: int, left: float, top: float, right: float, bottom: float
) -> bool:
    """Whether what ``child`` draws beyond its rect stays outside the bounds as its rect does."""
    out_l, out_t, out_r, out_b = _outsets(child)
    return x - out_l >= right or y - out_t >= bottom or x + w + out_r <= left or y + h + out_b <= top


def _replay_child(
    child: Any,
    canvas: Any,
    x: int,
    y: int,
    w: int,
    h: int,
    replay: _Replay,
    clip: Optional[Tuple[float, float, float, float]],
) -> bool:
    """Draw a child from its recording, recording it first when it has none.

    ``clip`` is the canvas clip in local coordinates, ``None`` when the caller
    has not read it.

    Returns:
        ``False`` when the child has to be painted directly.
    """
    _, scale_x, scale_y, translate_x, translate_y = replay
    device_x = scale_x * x + translate_x
    device_y = scale_y * y + translate_y
    key = (w, h, scale_x, scale_y)

    last = child._replay_key
    if last is not None and (child._replay_dirty or last != key):
        if not _stale_paints:
            # Not recorded now: a child that changes every frame would be recorded every frame.
            # Anything the paint below invalidates marks the child again.
            child._replay_dirty = False
            child._replay_key = key
            child._replay_picture = None
        return False
    picture = child._replay_picture
    if picture is not None:
        origin_x, origin_y = child._replay_origin
        canvas.save()
        canvas.resetMatrix()
        canvas.translate(device_x - origin_x, device_y - origin_y)
        canvas.drawPicture(picture)
        canvas.restore()
        return True

    if _stale_paints:
        return False
    child._replay_dirty = False
    child._replay_key = key
    if _recording is not None or child._replay_skip:
        return False
    return _record_child(child, canvas, x, y, w, h, replay, clip)


def _record_child(
    child: Any,
    canvas: Any,
    x: int,
    y: int,
    w: int,
    h: int,
    replay: _Replay,
    clip: Optional[Tuple[float, float, float, float]],
) -> bool:
    """Record a child and draw the recording, keeping it when it holds all the child draws.

    Returns:
        ``False`` when the child is not recorded.
    """
    global _recording, _recording_cut
    matrix, scale_x, scale_y, translate_x, translate_y = replay
    if clip is None:
        clip = local_clip_bounds(canvas)
        if clip is None:
            return False
    clip_l, clip_t, clip_r, clip_b = clip
    out_l, out_t, out_r, out_b = _outsets(child)
    left = x - out_l - _CULL_SLACK
    top = y - out_t - _CULL_SLACK
    right = x + w + out_r + _CULL_SLACK
    bottom = y + h + out_b + _CULL_SLACK
    if left >= clip_r or top >= clip_b or right <= clip_l or bottom <= clip_t:
        # A child that overflows a parent inside the clip was not culled.
        return False
    if w > clip_r - clip_l or h > clip_b - clip_t:
        # Recorded whole, it would paint what the clip hides.
        return False
    skia = get_skia(raise_if_missing=False)
    if skia is None or not _subtree_replay_safe(child):
        child._replay_skip = True
        return False

    # Out to the clip: a descendant may draw beyond the child's rect.
    x0 = scale_x * min(left, clip_l) + translate_x
    x1 = scale_x * max(right, clip_r) + translate_x
    y0 = scale_y * min(top, clip_t) + translate_y
    y1 = scale_y * max(bottom, clip_b) + translate_y
    recorder = skia.PictureRecorder()
    target = recorder.beginRecording(skia.Rect.MakeLTRB(-_FAR, -_FAR, _FAR, _FAR))
    # The recording carries the canvas matrix, so a widget that rasterises its
    # own cache at the device scale sees the scale it will be shown at.
    target.setMatrix(matrix)
    child._paint_inside_clip = True
    _recording = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    _recording_cut = False
    try:
        child.paint(target, x, y, w, h)
    finally:
        _recording = None
    picture = recorder.finishRecordingAsPicture()

    canvas.save()
    canvas.resetMatrix()
    canvas.drawPicture(picture)
    canvas.restore()
    if _recording_cut:
        # Replayed elsewhere it would lack the widget left out. Its children are recorded instead.
        child._replay_skip = True
    else:
        child._replay_picture = picture
        child._replay_origin = (scale_x * x + translate_x, scale_y * y + translate_y)
    return True


def paint_pending_child(child: "Widget", canvas: Any, x: int, y: int, width: int, height: int) -> None:
    """Paint a child the layout left pending, from its last layout.

    The child is painted at the size of that layout, its top left corner at
    ``(x, y)``. On a side where its rect is smaller now, what falls beyond the
    rect and its ``paint_outsets`` is cut. A child never laid out is painted
    as nothing. Its ``last_rect`` is the rect it has now in both cases.

    Args:
        child: The pending child.
        canvas: The canvas to paint on.
        x: The left edge of the child's rect on the canvas.
        y: The top edge of the child's rect on the canvas.
        width: The width of the child's rect.
        height: The height of the child's rect.
    """
    global _stale_paints

    size = child._laid_out_size
    if size is not None:
        clipped = False
        skia = get_skia(raise_if_missing=False)
        shrank = size[0] > width or size[1] > height
        if shrank and skia is not None and getattr(canvas, "save", None) is not None:
            # The other sides stay open: what its subtree draws beyond them is not in its outsets.
            _, _, out_r, out_b = _outsets(child)
            right = x + width + out_r if size[0] > width else _FAR
            bottom = y + height + out_b if size[1] > height else _FAR
            canvas.save()
            clipped = True
            clip_rect(canvas, skia.Rect.MakeLTRB(-_FAR, -_FAR, right, bottom))
        _stale_paints += 1
        try:
            replay = _replay_of(canvas)
            if replay is None or not _replay_child(child, canvas, x, y, size[0], size[1], replay, None):
                child.paint(canvas, x, y, size[0], size[1])
        finally:
            _stale_paints -= 1
            if clipped:
                canvas.restore()
    child.set_last_rect(x, y, width, height)


def paint_children_at_layout_rects(
    children: Sequence["Widget"],
    canvas: Any,
    x: int,
    y: int,
    *,
    inside_clip: bool = False,
) -> None:
    """Paint each laid-out child at ``(x, y)`` plus its layout rect.

    A child left pending by the layout is painted from its last layout
    (:func:`paint_pending_child`). A child whose layout rect plus
    ``paint_outsets`` ends beyond the canvas clip and a small slack is not
    painted. It still gets its ``last_rect``. A child that draws outside its
    rect must report that through ``paint_outsets``. With no readable clip, no
    canvas or a stand-in, every child is painted.

    A child whose subtree declares its drawing ``replay_safe`` is drawn from a
    recording, not painted, while nothing at or below it has invalidated.

    Args:
        children: The children to paint.
        canvas: The canvas to paint on.
        x: The left edge of the parent on the canvas.
        y: The top edge of the parent on the canvas.
        inside_clip: The parent lies wholly inside the clip, so no child is
            culled.
    """
    replay = _replay_of(canvas)

    if inside_clip:
        for child in children:
            rect = child.layout_rect
            if rect is None:
                if __debug__:
                    warn_child_without_rect(child)
                continue
            rel_x, rel_y, w, h = rect
            abs_x = x + rel_x
            abs_y = y + rel_y
            if child._layout_pending:
                paint_pending_child(child, canvas, abs_x, abs_y, w, h)
                continue
            child.set_last_rect(abs_x, abs_y, w, h)
            if replay is not None and _replay_child(child, canvas, abs_x, abs_y, w, h, replay, None):
                continue
            child._paint_inside_clip = True
            child.paint(canvas, abs_x, abs_y, w, h)
        return

    _paint_culled(children, canvas, x, y, local_clip_bounds(canvas), replay)


def _paint_culled(
    children: Sequence["Widget"],
    canvas: Any,
    x: int,
    y: int,
    clip: Optional[Tuple[float, float, float, float]],
    replay: Optional[_Replay],
) -> None:
    """Paint each child the clip and the recording under way reach; ``clip`` is ``None`` when it is unknown."""
    global _recording_cut

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

    # With no matrix to map its bounds through, the recording leaves nothing out here.
    held = _recording if replay is not None else None
    if held is not None and replay is not None:
        _, scale_x, scale_y, translate_x, translate_y = replay
        x0 = (held[0] - translate_x) / scale_x
        x1 = (held[2] - translate_x) / scale_x
        y0 = (held[1] - translate_y) / scale_y
        y1 = (held[3] - translate_y) / scale_y
        held_left, held_right = min(x0, x1), max(x0, x1)
        held_top, held_bottom = min(y0, y1), max(y0, y1)
    else:
        held_left = held_top = -math.inf
        held_right = held_bottom = math.inf

    for child in children:
        rect = child.layout_rect
        if rect is None:
            if __debug__:
                warn_child_without_rect(child)
            continue

        rel_x, rel_y, w, h = rect
        abs_x = x + rel_x
        abs_y = y + rel_y

        child.set_last_rect(abs_x, abs_y, w, h)

        outsets_only = False
        if abs_x >= clip_right or abs_y >= clip_bottom or abs_x + w <= clip_left or abs_y + h <= clip_top:
            if _outsets_outside(child, abs_x, abs_y, w, h, clip_left, clip_top, clip_right, clip_bottom):
                if child._replay_key is not None:
                    _forget_pictures(child)
                continue
            outsets_only = True
        if (
            held is not None
            and (abs_x >= held_right or abs_y >= held_bottom or abs_x + w <= held_left or abs_y + h <= held_top)
            and _outsets_outside(child, abs_x, abs_y, w, h, held_left, held_top, held_right, held_bottom)
        ):
            _recording_cut = True
            if child._replay_key is not None:
                _forget_pictures(child)
            continue

        if child._layout_pending:
            paint_pending_child(child, canvas, abs_x, abs_y, w, h)
            continue

        if outsets_only:
            if replay is not None and not _stale_paints:
                # Painted, so that leaving the clip gives up what is recorded below it.
                child._replay_dirty = False
                child._replay_key = (w, h, replay[1], replay[2])
        elif replay is not None and _replay_child(child, canvas, abs_x, abs_y, w, h, replay, clip):
            continue
        elif abs_x >= in_left and abs_y >= in_top and abs_x + w <= in_right and abs_y + h <= in_bottom:
            child._paint_inside_clip = True

        child.paint(canvas, abs_x, abs_y, w, h)
