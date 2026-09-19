"""Human-facing feedback for comment mode and the source jump.

The visual half of :mod:`nuiitivet.dev.comment_mode`: a pure function of the
live :class:`~nuiitivet.dev.comments.Comments`, read at paint time. Drawn from
the live frame paths only, outside the widget tree, so ``describe_tree`` never
sees a mark and ``screenshot`` never contains one. Amber, against the action
overlay's indigo: "the human means this", not "the assistant did this".

While latched: the HUD badge (:mod:`.hud`), a hover highlight on the pick
candidate, the newest mark at full strength, earlier ones dimmed to their
badges, and the field open on a mark. After committing: numbered badges only,
each with its instruction beside it, cut short, plus one line at the badge's
home saying what to type in chat until the assistant has read the comments.
Widgets get corner brackets and areas a faint fill, so the two kinds of mark
stay distinct when they nest.

The source jump (:mod:`nuiitivet.dev.source_jump`) paints here too, in rose:
brackets and a caption on the widget a chorded click would open, then what the
jump did.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from nuiitivet._interaction.perception import visible_rect

from .comment_mode import BADGE_RADIUS
from .hud import FONT_SIZE, SEPARATOR, color, hud_font, paint_caption, paint_hud
from .inline_field import paint_field

logger = logging.getLogger(__name__)

# Truthy/falsy spellings accepted for the disable env var, shared with the
# action overlay so one switch turns off all dev-only drawing.
_FALSY = {"0", "false", "no", "off"}

# Amber: "the human means this".
_ACCENT = (255, 171, 0)
# Rose, for the source jump: its brackets must not read as a mark about to be made.
_JUMP_ACCENT = (236, 64, 122)
# Ink for the numbered badges.
_BADGE_INK = (32, 24, 0)

_BRACKET_LEN = 12.0
_BRACKET_WIDTH = 2.5
#: What to type in chat, shown until the comments are read. The fallback is the
#: tool's name, not a sentence: "see the comments" reads as code comments.
PROMPT = "in chat: /nuiitivet-see-comments" + SEPARATOR + "see_comments"
# Characters of an instruction shown beside its badge before it is cut short.
_CAPTION_CHARS = 32
# The field's least size beside a badge; it grows with the text.
_FIELD_SIZE = (180.0, 24.0)


def _enabled() -> bool:
    return os.environ.get("NUIITIVET_DEV_ACTION_OVERLAY", "1").strip().lower() not in _FALSY


def paint_comments(app: Any, canvas: Any, width: int, height: int) -> None:
    """Paint comment mode's and the source jump's feedback over the just-painted tree.

    Called from the live frame paths after the tree is painted, never from
    ``App._render_snapshot``. Failures are swallowed: a decoration must never
    break the frame.
    """
    if not _enabled():
        return
    mode = getattr(app, "_comment_mode", None)
    jump = getattr(app, "_source_jump", None)
    if mode is None and jump is None:
        return
    try:
        comments = mode.comments if mode is not None else None
        active = bool(mode.active) if mode is not None else False
        marks = comments.marks() if comments is not None else []
        jump_target = jump.hovered if jump is not None else None
        jump_notice = jump.notice if jump is not None else None
        editing = getattr(app, "_layout_edit_mode", None)
        # With no mode latched the badge's home is free for the prompt and the jump's notice.
        alone = not active and not (editing is not None and editing.active)
        unread = alone and comments is not None and comments.unread
        if not active and not marks and jump_target is None and not jump_notice:
            return

        from nuiitivet.rendering.skia.skia_module import get_skia

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return

        font, typeface = hud_font(skia)
        writing = mode.writing if active and mode is not None else None
        badges = _paint_marks(skia, canvas, app, comments, marks, active, writing, font, typeface)

        if active and mode is not None and comments is not None:
            if mode.band is not None:
                _paint_band(skia, canvas, mode.band)
            _paint_hover(skia, canvas, mode, font, typeface, comments.members(), skip=jump_target)
            _paint_hud(skia, canvas, mode, marks, jump_notice, font, typeface, width, height)
            _paint_open_field(skia, canvas, app, writing, badges, font, typeface)
        # Only in a window that shows a mark.
        prompt = PROMPT if unread and badges else None
        if jump_target is not None:
            _paint_jump(skia, canvas, jump_target, jump_notice, font, typeface)
        elif alone and (prompt or jump_notice):
            _paint_home(skia, canvas, [prompt, jump_notice], font, typeface, width, height)
    except Exception:
        logger.debug("comment_overlay: paint failed", exc_info=True)


def _paint_marks(
    skia: Any,
    canvas: Any,
    app: Any,
    comments: Any,
    marks: list[tuple[int, str, Any]],
    active: bool,
    writing: Any,
    font: Any,
    typeface: Any,
) -> dict[int, tuple[float, float]]:
    """Paint every mark this window owns; return where each one's badge landed, by number."""
    from nuiitivet.widgeting.context_lookup import find_window

    newest_index = marks[-1][0] if marks else None
    badges: dict[int, tuple[float, float]] = {}
    for index, kind, mark in marks:
        if kind != "region":
            # The buffer spans windows: a node's mark paints only in the window
            # that owns it. Regions carry no owner and paint in every window.
            owner = find_window(mark)
            if owner is not None and owner is not app:
                continue
        rect = mark if kind == "region" else visible_rect(mark)
        if rect is None:
            continue
        # Only the newest mark is drawn in full, and only while marking.
        full = active and index == newest_index
        if kind == "region":
            # A wash, not an outline: nested with a node's brackets, two strokes would not read.
            _paint_wash(skia, canvas, rect, 0.22 if full else 0.13)
        elif full:
            paint_brackets(skia, canvas, rect, 1.0)
        _paint_badge(skia, canvas, rect, str(index), font, typeface, 1.0 if full else 0.75)
        badges[index] = (rect[0], rect[1])
        instruction = comments.instruction(index) if comments is not None else None
        if instruction and (writing is None or writing.index != index):
            paint_caption(skia, canvas, _shortened(instruction), font, typeface, *_beside(rect))
    return badges


def _paint_open_field(
    skia: Any, canvas: Any, app: Any, writing: Any, badges: dict[int, tuple[float, float]], font: Any, typeface: Any
) -> None:
    """The field open on a mark, beside its badge and above everything else the mode paints."""
    if writing is not None and writing.index in badges:
        x, y = _beside(badges[writing.index])
        paint_field(skia, canvas, app, (x, y, *_FIELD_SIZE), writing.field.value, _ACCENT, font, typeface)


def _paint_home(
    skia: Any, canvas: Any, notices: list[Optional[str]], font: Any, typeface: Any, width: int, height: int
) -> None:
    """Lines at the badge's home with no mode latched: the read prompt, the jump's notice."""
    paint_hud(
        skia,
        canvas,
        mode_line=None,
        hints=(),
        notices=notices,
        placement=None,
        pointer=None,
        font=font,
        typeface=typeface,
        width=width,
        height=height,
    )


def paint_brackets(
    skia: Any, canvas: Any, rect: tuple[float, ...], alpha: float, rgb: tuple[int, int, int] = _ACCENT
) -> None:
    """Draw four corner brackets -- "this object", as distinct from "this area"."""
    x, y, w, h = rect
    arm = min(_BRACKET_LEN, max(2.0, w / 3.0), max(2.0, h / 3.0))
    paint = skia.Paint(AntiAlias=True)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(_BRACKET_WIDTH)
    paint.setColor(color(skia, rgb, alpha))
    for cx, sx in ((x, 1.0), (x + w, -1.0)):
        for cy, sy in ((y, 1.0), (y + h, -1.0)):
            canvas.drawLine(cx, cy, cx + arm * sx, cy, paint)
            canvas.drawLine(cx, cy, cx, cy + arm * sy, paint)


def _paint_wash(skia: Any, canvas: Any, rect: tuple[float, ...], alpha: float) -> None:
    """Fill a marked area -- "this region", as distinct from "this object"."""
    x, y, w, h = rect
    paint = skia.Paint(AntiAlias=True)
    paint.setColor(color(skia, _ACCENT, alpha))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint)


def _paint_band(skia: Any, canvas: Any, rect: tuple[float, ...]) -> None:
    """Draw the rect a drag has swept so far, so the human can aim before letting go."""
    x, y, w, h = rect
    _paint_wash(skia, canvas, rect, 0.18)
    stroke = skia.Paint(AntiAlias=True)
    stroke.setStyle(skia.Paint.kStroke_Style)
    stroke.setStrokeWidth(1.5)
    stroke.setColor(color(skia, _ACCENT, 0.9))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), stroke)


def _paint_badge(
    skia: Any,
    canvas: Any,
    rect: tuple[float, ...],
    label: str,
    font: Any,
    typeface: Any,
    alpha: float,
) -> None:
    """Draw the numbered pin at a mark's top-left corner; the number is the payload's ``index``."""
    x, y, _w, _h = rect
    disc = skia.Paint(AntiAlias=True)
    disc.setColor(color(skia, _ACCENT, alpha))
    canvas.drawCircle(x, y, BADGE_RADIUS, disc)
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    blob = make_text_blob(label, font)
    if blob is None:
        return
    text_w = measure_text_width(typeface, FONT_SIZE, label)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, _BADGE_INK, alpha))
    canvas.drawTextBlob(blob, x - text_w / 2.0, y + FONT_SIZE / 2.5, ink)


def _paint_hover(
    skia: Any,
    canvas: Any,
    mode: Any,
    font: Any,
    typeface: Any,
    members: list[Any],
    *,
    skip: Any = None,
) -> None:
    """Outline the pick candidate and name it, so the human can aim before clicking.

    ``skip`` is the widget the source jump is bracketing, whose caption wins.
    """
    candidate = mode.hovered
    if candidate is None or candidate is skip or any(candidate is member for member in members):
        return
    rect = visible_rect(candidate)
    if rect is None:
        return
    x, y, w, h = rect
    wash = skia.Paint(AntiAlias=True)
    wash.setColor(color(skia, _ACCENT, 0.16))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), wash)
    paint_brackets(skia, canvas, rect, 0.7)
    paint_caption(skia, canvas, describe_node(candidate), font, typeface, x, max(0.0, y - 22.0))


def _beside(at: tuple[float, ...]) -> tuple[float, float]:
    """Where a caption or field sits next to the badge on ``at``'s corner."""
    return (at[0] + BADGE_RADIUS + 4.0, at[1] - 10.0)


def _shortened(instruction: str) -> str:
    """The instruction as the badge shows it: one line, cut short."""
    line = instruction.splitlines()[0] if instruction else ""
    return line if len(line) <= _CAPTION_CHARS else line[: _CAPTION_CHARS - 1] + "…"


def _paint_jump(
    skia: Any,
    canvas: Any,
    target: Any,
    notice: Optional[str],
    font: Any,
    typeface: Any,
) -> None:
    """Bracket the widget a chorded click would open, and say what the last jump did.

    The notice replaces the caption until the next pointer move clears it.
    """
    rect = visible_rect(target)
    if rect is None:
        return
    x, y, _w, _h = rect
    paint_brackets(skia, canvas, rect, 0.8, _JUMP_ACCENT)
    text = notice if notice else describe_node(target)
    paint_caption(skia, canvas, text, font, typeface, x, max(0.0, y - 22.0))


def describe_node(node: Any) -> str:
    """Name a widget the way ``describe_tree`` would, plus where it was built."""
    from nuiitivet.dev.interaction import resolve_target

    identity = resolve_target(node)
    name = identity.get("key") or identity.get("label")
    head = identity.get("type", type(node).__name__)
    label = f"{head}  {name}" if name else str(head)
    # Where it was built. Shown so the jump gesture is discoverable
    # without adding anything pressable to a paint-only overlay -- seeing the
    # location is what tells the human it can be reached. Basename only: the
    # caption has to stay readable in a window a few hundred pixels wide.
    where = _origin(node)
    return f"{label}{SEPARATOR}{where}" if where else label


def _origin(node: Any) -> Optional[str]:
    """``file:line`` for the node's construction site, or ``None``."""
    from nuiitivet.dev.source import site_of

    site = site_of(node)
    if not site:
        return None
    return f"{os.path.basename(site[0].file)}:{site[0].line}"


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _paint_hud(
    skia: Any,
    canvas: Any,
    mode: Any,
    marks: list[tuple[int, str, Any]],
    jump_notice: Optional[str],
    font: Any,
    typeface: Any,
    width: int,
    height: int,
) -> None:
    """The badge while latched: the mode, its counts and exits, then the keys that apply now."""
    regions = sum(1 for _index, kind, _mark in marks if kind == "region")
    parts = [_plural(len(marks) - regions, "widget")]
    if regions:
        parts.append(_plural(regions, "region"))

    mode_line = SEPARATOR.join(("COMMENT", "for the assistant", *parts, mode.exit, "Ctrl+Shift+E edit"))
    paint_hud(
        skia,
        canvas,
        mode_line=mode_line,
        hints=mode.hints,
        notices=[jump_notice],
        placement=mode.placement,
        pointer=mode.pointer,
        font=font,
        typeface=typeface,
        width=width,
        height=height,
    )


__all__ = [
    "PROMPT",
    "describe_node",
    "paint_brackets",
    "paint_comments",
]
