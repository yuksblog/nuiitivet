"""Comment mode's feedback on the glass, and the source jump's.

A pure function of the mode and the :class:`~nuiitivet.dev.comments.Comments`
buffer, read at paint time, drawn from the live frame paths only and never
into the widget tree, so ``describe_tree`` never sees a mark and ``screenshot``
never contains one. While latched it paints the hover candidate, every mark's
numbered badge, the instruction under the pointer, the open field and the
badge; after a commit, the line saying what to type in chat until the agent
has read the comments; and for the source jump, its brackets and its notice.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from nuiitivet._interaction.perception import visible_rect

from nuiitivet.widgets.text_lines import break_lines

from .comment_mode import BADGE_RADIUS, BESIDE_GAP, FIELD_LEAST, beside_anchor
from .hud import (
    FONT_SIZE,
    SEPARATOR,
    caption_size,
    color,
    hud_font,
    paint_caption,
    paint_hud,
    paint_sheet,
    paint_splash,
)
from .inline_field import Slot, measure, paint_field

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
#: What to type in chat, shown until the comments are read.
PROMPT = "in chat: /nuiitivet-see-comments" + SEPARATOR + "see_comments"

#: Every gesture of the mode, for the sheet ``H`` holds open.
HELP: tuple[tuple[str, str], ...] = (
    ("Esc", "discard the session and leave"),
    ("Click", "mark the widget"),
    ("Drag", "mark an area"),
    ("W / A / S / D", "walk to the parent, siblings and child"),
    ("Enter", "mark the walked widget; else keep all and leave"),
    ("Enter (in the field)", "keep the text"),
    ("Shift+Enter (in the field)", "new line"),
    ("Esc (in the field)", "close the field"),
    ("Delete / Backspace", "remove the mark under the pointer"),
    ("Ctrl+Z / Ctrl+Shift+Z", "undo / redo"),
    ("Ctrl+Backspace", "remove every mark"),
)


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
        splash = mode.splash if mode is not None else None
        if not active and not marks and jump_target is None and not jump_notice and not splash:
            return

        from nuiitivet.rendering.skia.skia_module import get_skia

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return

        font, typeface = hud_font(skia)
        window = (float(width), float(height))
        writing = mode.writing if active and mode is not None else None
        hovered_badge = mode.hovered_badge if active and mode is not None else None
        if active and mode is not None:
            if mode.band is not None:
                _paint_band(skia, canvas, mode.band)
            # Under the badges: a marked widget hovers like any other, its badge on top.
            _paint_hover(skia, canvas, mode, font, typeface, window, skip=jump_target)
        badges = _paint_marks(skia, canvas, app, comments, marks, writing, hovered_badge, font, typeface, window)
        if active and mode is not None:
            _paint_hud(skia, canvas, mode, jump_notice, font, typeface, width, height)
            _paint_open_field(skia, canvas, app, writing, badges, font, typeface, window)
            if mode.help:
                paint_sheet(skia, canvas, "COMMENT MODE", HELP, font, typeface, *window)
        # Only in a window that shows a mark.
        prompt = PROMPT if unread and badges else None
        if jump_target is not None:
            _paint_jump(skia, canvas, jump_target, jump_notice, font, typeface, window)
        elif alone and (prompt or jump_notice):
            _paint_home(skia, canvas, [prompt, jump_notice], font, typeface, width, height)
        if splash:
            paint_splash(skia, canvas, splash, font, typeface, *window)
    except Exception:
        logger.debug("comment_overlay: paint failed", exc_info=True)


def _paint_marks(
    skia: Any,
    canvas: Any,
    app: Any,
    comments: Any,
    marks: list[tuple[int, str, Any]],
    writing: Any,
    hovered_badge: Optional[int],
    font: Any,
    typeface: Any,
    window: tuple[float, float],
) -> dict[int, tuple[float, float]]:
    """Paint every mark this window owns; return where each one's badge landed, by number.

    Nothing but the number sits beside a mark; its instruction shows whole
    while the pointer rests on the badge.
    """
    from nuiitivet.widgeting.context_lookup import find_window

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
        if kind == "region":
            # A wash, so the area reads as one even where it crosses widgets.
            _paint_wash(skia, canvas, rect, 0.13)
        _paint_badge(skia, canvas, rect, str(index), font, typeface, 0.75)
        badges[index] = (rect[0], rect[1])
        instruction = comments.instruction(index) if comments is not None else None
        if instruction and index == hovered_badge and (writing is None or writing.index != index):
            # Wrapped where the field would wrap it, so reading and writing show the same lines.
            slot = Slot.beside(beside_anchor(rect), FIELD_LEAST, BESIDE_GAP, window)
            caption = _wrapped(instruction, slot.wrap)
            at = slot.place(caption_size(caption, typeface), window)
            paint_caption(skia, canvas, caption, font, typeface, *at)
    return badges


def _paint_open_field(
    skia: Any,
    canvas: Any,
    app: Any,
    writing: Any,
    badges: dict[int, tuple[float, float]],
    font: Any,
    typeface: Any,
    window: tuple[float, float],
) -> None:
    """The field open on a mark, beside its badge and above everything else the mode paints."""
    if writing is not None and writing.index in badges:
        slot = writing.slot.moved(beside_anchor(badges[writing.index]))
        paint_field(skia, canvas, app, slot, writing.field.value, _ACCENT, font, typeface, window)


def _paint_home(
    skia: Any, canvas: Any, notices: list[Optional[str]], font: Any, typeface: Any, width: int, height: int
) -> None:
    """Lines in the box at the bottom-left with no mode latched: the read prompt, the jump's notice."""
    paint_hud(
        skia,
        canvas,
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
    """Draw four corner brackets on ``rect``: the mark of a widget."""
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
    """Fill ``rect`` faintly: the mark of an area."""
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
    window: tuple[float, float],
    *,
    skip: Any = None,
) -> None:
    """Outline the pick candidate and name it, so the human can aim before clicking.

    Nothing while the pointer rests on a badge, where a click reopens the
    field instead. ``skip`` is the widget the source jump is bracketing, whose
    caption wins.
    """
    candidate = mode.hovered
    if candidate is None or candidate is skip or mode.hovered_badge is not None:
        return
    rect = visible_rect(candidate)
    if rect is None:
        return
    x, y, w, h = rect
    wash = skia.Paint(AntiAlias=True)
    wash.setColor(color(skia, _ACCENT, 0.16))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), wash)
    paint_brackets(skia, canvas, rect, 0.7)
    paint_caption(skia, canvas, describe_node(candidate), font, typeface, x, y - 22.0, window)


def _wrapped(instruction: str, width: Optional[float]) -> str:
    """The whole instruction, its own line breaks kept and long lines broken at ``width``."""
    lines = break_lines(instruction, measure, width)
    return "\n".join(instruction[line.start : line.end] for line in lines)


def _paint_jump(
    skia: Any,
    canvas: Any,
    target: Any,
    notice: Optional[str],
    font: Any,
    typeface: Any,
    window: tuple[float, float],
) -> None:
    """Bracket the widget a chorded click would open, and say what the last jump did.

    The notice replaces the caption until the next pointer move clears it.
    """
    rect = visible_rect(target)
    if rect is None:
        return
    x, y, _w, _h = rect
    paint_brackets(skia, canvas, rect, 0.8, _JUMP_ACCENT)
    text = notice if notice else describe_node(target, site=True)
    paint_caption(skia, canvas, text, font, typeface, x, y - 22.0, window)


def describe_node(node: Any, *, site: bool = False) -> str:
    """Name a widget the way ``describe_tree`` would; with ``site``, add where it was built."""
    from nuiitivet.dev.interaction import resolve_target

    identity = resolve_target(node)
    name = identity.get("key") or identity.get("label")
    head = identity.get("type", type(node).__name__)
    label = f"{head}  {name}" if name else str(head)
    if not site:
        return label
    # Basename only: the caption has to stay readable in a window a few hundred pixels wide.
    where = _origin(node)
    return f"{label}{SEPARATOR}{where}" if where else label


def _origin(node: Any) -> Optional[str]:
    """``file:line`` for the node's construction site, or ``None``."""
    from nuiitivet.dev.source import site_of

    site = site_of(node)
    if not site:
        return None
    return f"{os.path.basename(site[0].file)}:{site[0].line}"


def _paint_hud(
    skia: Any,
    canvas: Any,
    mode: Any,
    jump_notice: Optional[str],
    font: Any,
    typeface: Any,
    width: int,
    height: int,
) -> None:
    """The box at the bottom-left while latched: the jump's notice, when there is one."""
    paint_hud(
        skia,
        canvas,
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
