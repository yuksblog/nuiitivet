"""Comment mode's feedback on the glass, and the source jump's.

A pure function of the mode and the :class:`~nuiitivet.dev.comments.Comments`
buffer, read at paint time, drawn from the live frame paths only and never
into the widget tree, so ``describe_tree`` never sees a mark and ``screenshot``
never contains one. While latched it paints every mark's numbered badge,
with a glyph for the agent's answer, the hover candidate, the thread under
the pointer, the open field and the send button; off, no mark, since the
human left to use the app. For the source jump, its brackets and its notice.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from nuiitivet._interaction.perception import visible_rect
from nuiitivet.material.symbols.material_symbols import Symbols
from nuiitivet.widgets.text_lines import break_lines

from .comment_mode import ANSWER_WIDTH, BADGE_RADIUS, FIELD_LEAST, SEND_PEEK, UNDER_GAP, send_button_rect
from .hud import (
    CAPTION_INK,
    FONT_SIZE,
    ICON_GUTTER,
    LINE_HEIGHT,
    MARGIN,
    PAD,
    SEPARATOR,
    Row,
    color,
    fit_inside,
    hud_font,
    paint_caption,
    paint_hud,
    paint_rows,
    paint_sheet,
    paint_splash,
    rows_size,
    symbol_font,
)
from .inline_field import field_rect, measure, paint_field

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
Rect = tuple[float, ...]
#: The Material Symbols glyph beside the number once the agent has answered, by outcome.
GLYPHS = {
    "done": Symbols.check.codepoint,
    "refused": Symbols.close.codepoint,
    "question": Symbols.question_mark.codepoint,
}
#: The glyph beside the number of a sent mark the agent has not answered yet.
AWAITING_GLYPH = Symbols.hourglass_empty.codepoint
# The glyph's size in the badge.
_GLYPH_SIZE = 14.0
#: The disc behind each glyph: green for done, red for refused, blue for a question, grey while awaiting.
GLYPH_COLOURS = {
    GLYPHS["done"]: (67, 160, 71),
    GLYPHS["refused"]: (229, 57, 53),
    GLYPHS["question"]: (30, 136, 229),
    AWAITING_GLYPH: (117, 117, 117),
}
#: The icon leading a thread row, by who wrote the line.
ICONS = {"human": Symbols.person.codepoint, "agent": Symbols.smart_toy.codepoint}
#: The send button's icon and word.
SEND_GLYPH = Symbols.send.codepoint
_SEND_LABEL = "Send"

#: Every gesture of the mode, for the sheet ``H`` holds open.
HELP: tuple[tuple[str, str], ...] = (
    ("Ctrl+Enter, or Send (bottom-right)", "send the comments to the agent; from the field, keep the text too"),
    ("Esc", "leave; every mark stays"),
    ("Click", "mark the widget"),
    ("Click (on a mark)", "edit the text, or reply to the answer"),
    ("Drag", "mark an area"),
    ("W / A / S / D", "walk to the parent, siblings and child"),
    ("Enter", "mark the walked widget"),
    ("Enter (in the field)", "keep the text"),
    ("Shift+Enter (in the field)", "new line"),
    ("Esc (in the field)", "close the field; a new mark with nothing written goes too"),
    ("Delete / Backspace", "remove the mark under the pointer"),
    ("Ctrl+Z / Ctrl+Shift+Z", "undo / redo, back to the last send"),
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
        # Off, the marks wait unseen in the buffer: the human left to use the app.
        marks = comments.marks() if comments is not None and active else []
        jump_target = jump.hovered if jump is not None else None
        jump_notice = jump.notice if jump is not None else None
        editing = getattr(app, "_layout_edit_mode", None)
        # With no mode latched the notice box is free for the jump's notice.
        alone = not active and not (editing is not None and editing.active)
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
        rects, thread = _paint_marks(skia, canvas, app, comments, marks, writing, hovered_badge, font, typeface)
        if active and mode is not None:
            _paint_hud(skia, canvas, mode, jump_notice, font, typeface, width, height)
            _paint_send(skia, canvas, mode.send_raised, font, typeface, window)
            # Over every mark: a thread read under another mark's badge is a thread not read.
            _paint_under_mark(skia, canvas, app, thread, writing, rects, font, typeface, window)
            if mode.help:
                paint_sheet(skia, canvas, "COMMENT MODE", HELP, font, typeface, *window)
        if jump_target is not None:
            _paint_jump(skia, canvas, jump_target, jump_notice, font, typeface, window)
        elif alone and jump_notice:
            _paint_home(skia, canvas, [jump_notice], font, typeface, width, height)
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
) -> tuple[dict[int, Rect], Optional[tuple[str, Rect]]]:
    """Paint every mark this window owns.

    Returns each one's rect, by number, and the thread to paint last with the
    rect of its mark: the mark whose field is open, else the one whose badge
    the pointer rests on, or ``None``. Nothing but the number sits beside a
    mark, joined by an hourglass once sent and by the answer's glyph once the
    agent has answered.
    """
    from nuiitivet.widgeting.context_lookup import find_window

    rects: dict[int, Rect] = {}
    thread_to_paint: Optional[tuple[Any, Rect]] = None
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
        outcome = comments.outcome(index) if comments is not None else None
        glyph = GLYPHS.get(outcome or "")
        if glyph is None and comments is not None and comments.awaiting(index):
            glyph = AWAITING_GLYPH
        _paint_badge(skia, canvas, rect, str(index), glyph, font, typeface, 1.0)
        rects[index] = tuple(rect)
        thread = comments.thread(index) if comments is not None else ()
        # The thread of the mark being written on, so the reply is written with the exchange in view;
        # else the one under the pointer.
        shown = writing.index if writing is not None else hovered_badge
        if thread and index == shown:
            thread_to_paint = (thread, tuple(rect))
    return (rects, thread_to_paint)


def _paint_under_mark(
    skia: Any,
    canvas: Any,
    app: Any,
    thread: Optional[tuple[Any, Rect]],
    writing: Any,
    rects: dict[int, Rect],
    font: Any,
    typeface: Any,
    window: tuple[float, float],
) -> None:
    """The thread, then the open field, stacked under the mark's badge, or above it when the window ends there.

    ``thread`` is the lines and the rect of the mark whose thread shows; the
    field is the one open on that mark, or on a mark with no thread yet. Laid
    out as one block, so the field never lands on the thread it answers; a
    thread taller than the room keeps its newest rows.
    """
    if thread is not None:
        lines, rect = thread
    elif writing is not None and writing.index in rects:
        lines, rect = (), rects[writing.index]
    else:
        return
    x, y, _w, h = rect
    field = writing if writing is not None and writing.index in rects else None
    field_w = field_h = 0.0
    if field is not None:
        _fx, _fy, field_w, field_h = field_rect(field.slot.moved((x, 0.0)), field.field.text, window)
    rows: list[Row] = []
    if lines:
        wrap = max(FIELD_LEAST[0], window[0] - MARGIN - x) - PAD * 2 - ICON_GUTTER
        room = window[1] - MARGIN * 2 - (UNDER_GAP + field_h if field is not None else 0.0)
        rows = _tail(_thread_rows(lines, wrap), max(1, int(room // LINE_HEIGHT)))
    thread_box = rows_size(rows, typeface) if rows else (0.0, 0.0)
    block_w, block_h = max(thread_box[0], field_w), thread_box[1]
    if field is not None:
        block_h += (UNDER_GAP if rows else 0.0) + field_h
    top = y + BADGE_RADIUS + UNDER_GAP
    if top + block_h > window[1] - MARGIN:
        top = y - BADGE_RADIUS - UNDER_GAP - block_h
    x, top = fit_inside((x, top), (block_w, block_h), window)
    if rows:
        paint_rows(skia, canvas, rows, font, typeface, x, top)
        top += thread_box[1] + UNDER_GAP
    if field is not None:
        paint_field(skia, canvas, app, field.slot.moved((x, top)), field.field.value, _ACCENT, font, typeface, window)


def _thread_rows(lines: Any, wrap: float) -> list[Row]:
    """The thread as rows: each line's first row led by its writer's icon, its wrapped rest under it."""
    rows: list[Row] = []
    for line in lines:
        for row, text in enumerate(_wrapped(line.text, wrap).split("\n")):
            rows.append((ICONS[line.by] if row == 0 else None, text))
    return rows


def _tail(rows: list[Row], fit: int) -> list[Row]:
    """The newest ``fit`` rows, the first of them a count of what is cut, when ``rows`` do not all fit."""
    if len(rows) <= fit:
        return rows
    kept = rows[-(fit - 1) :] if fit > 1 else rows[-1:]
    cut = len(rows) - len(kept)
    return [(None, f"… {cut} earlier row{'' if cut == 1 else 's'}")] + kept


def _paint_home(
    skia: Any, canvas: Any, notices: list[Optional[str]], font: Any, typeface: Any, width: int, height: int
) -> None:
    """Lines in the box at the bottom-left with no mode latched: the jump's notice."""
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
    glyph: Optional[str],
    font: Any,
    typeface: Any,
    alpha: float,
) -> None:
    """Draw the numbered pin at a mark's top-left corner; the number is the payload's ``index``.

    With a ``glyph`` a second disc joins the pin on its right, in the glyph's
    colour, the glyph bold and light on it.
    """
    x, y, _w, _h = rect
    disc = skia.Paint(AntiAlias=True)
    disc.setColor(color(skia, _ACCENT, alpha))
    canvas.drawCircle(x, y, BADGE_RADIUS, disc)
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, _BADGE_INK, alpha))
    blob = make_text_blob(label, font)
    if blob is not None:
        text_w = measure_text_width(typeface, FONT_SIZE, label)
        canvas.drawTextBlob(blob, x - text_w / 2.0, y + FONT_SIZE / 2.5, ink)
    if glyph is None:
        return
    centre = x + BADGE_RADIUS + ANSWER_WIDTH / 2.0 - 2.0
    disc.setColor(color(skia, GLYPH_COLOURS[glyph], alpha))
    canvas.drawCircle(centre, y, BADGE_RADIUS, disc)
    icon_font, icon_typeface = symbol_font(_GLYPH_SIZE)
    blob = make_text_blob(glyph, icon_font) if icon_font is not None else None
    if blob is not None:
        # Stroked as well as filled, which is what makes the glyph bold.
        bold = skia.Paint(AntiAlias=True)
        bold.setColor(color(skia, CAPTION_INK, alpha))
        bold.setStyle(skia.Paint.kStrokeAndFill_Style)
        bold.setStrokeWidth(1.0)
        # An icon glyph stands on the baseline and rises its size; centred on its disc.
        glyph_w = measure_text_width(icon_typeface, _GLYPH_SIZE, glyph)
        canvas.drawTextBlob(blob, centre - glyph_w / 2.0, y + _GLYPH_SIZE / 2.0, bold)


def _paint_send(
    skia: Any, canvas: Any, raised: bool, font: Any, typeface: Any, window: tuple[float, float]
) -> None:
    """The send button at the bottom-right, a pill in the mode's amber: ``raised`` inside the margin, else sunk.

    Sunk, only an edge shows above the window's bottom, and the pointer on it raises the button.
    """
    x, y, w, h = send_button_rect(window)
    if not raised:
        y = window[1] - SEND_PEEK
    pill = skia.Paint(AntiAlias=True)
    pill.setColor(color(skia, _ACCENT, 1.0))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, h), h / 2.0, h / 2.0, pill)
    if font is None or not raised:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, _BADGE_INK, 1.0))
    icon_font, icon_typeface = symbol_font(_GLYPH_SIZE)
    icon_w = measure_text_width(icon_typeface, _GLYPH_SIZE, SEND_GLYPH) if icon_typeface is not None else 0.0
    text_w = measure_text_width(typeface, FONT_SIZE, _SEND_LABEL)
    left = x + (w - icon_w - UNDER_GAP - text_w) / 2.0
    blob = make_text_blob(SEND_GLYPH, icon_font) if icon_font is not None else None
    if blob is not None:
        # An icon glyph stands on the baseline and rises its size; centred on the pill.
        canvas.drawTextBlob(blob, left, y + (h + _GLYPH_SIZE) / 2.0, ink)
    blob = make_text_blob(_SEND_LABEL, font)
    if blob is not None:
        canvas.drawTextBlob(blob, left + icon_w + UNDER_GAP, y + h / 2.0 + FONT_SIZE / 2.5, ink)


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


def _wrapped(text: str, width: Optional[float]) -> str:
    """The whole ``text``, its own line breaks kept and long lines broken at ``width``."""
    lines = break_lines(text, measure, width)
    return "\n".join(text[line.start : line.end] for line in lines)


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
    "AWAITING_GLYPH",
    "GLYPHS",
    "ICONS",
    "SEND_GLYPH",
    "describe_node",
    "paint_brackets",
    "paint_comments",
]
