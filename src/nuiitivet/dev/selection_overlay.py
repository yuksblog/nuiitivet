"""Human-facing feedback for select mode and the source jump.

The visual half of :mod:`nuiitivet.dev.select_mode`. Where
:mod:`nuiitivet.dev.action_overlay` shows the human what the *assistant* just
did, this shows them what *they* are designating -- so the two must not look
alike. The action overlay's indigo means "the assistant did this"; this one uses
a distinct amber, because a designation means "the human means this", and one
visual language for opposite directions would be actively misleading.

Same hard constraint as the action overlay: markers are drawn from a **paint-only
path outside the widget tree**, and only from the live frame paths -- never from
``App._render_snapshot``. ``describe_tree`` must not see them, and ``screenshot``
must not contain them, or the assistant would end up reading its own human's
annotations back as app content.

Unlike the action overlay this holds no registry of its own: it is a pure
function of the live :class:`~nuiitivet.dev.selection.Selection`, read at paint
time. There is nothing to expire and no repaint pump to run.

**Two phases**, because what the human needs while designating and after
committing are different things:

* *While latched* -- the HUD badge (:mod:`.hud`), a hover highlight on the pick
  candidate, the newest designation at full strength, and every earlier one
  dimmed to its badge. Designation is sequential, so full legibility is only
  ever needed for the one just made; this is what keeps the overlay readable as
  the count grows. The HUD names each gesture at the moment it applies, because
  it is the only place a human can learn them -- there is no menu and no panel,
  and a key the badge never mentions is a key nobody finds.
* *After committing* (``Enter``) -- **numbered badges only**. The human is done
  pointing and wants to see their app again; the durable record lives in the
  payload, not on the glass. It is the numbered-pin behaviour every annotation
  tool converges on, and it also defuses the "latched mode left on obscures the
  screen" hazard.

Nodes are drawn as **corner brackets** rather than a full outline, so that when
region designation lands (drawn as a faint fill) the two
read as different *classes* of mark instead of two similar rectangles.

The source jump (:mod:`nuiitivet.dev.source_jump`) paints here too, in any
state: rose brackets and a caption on the widget a chorded click would open
while the chord is held, and what the last jump did once it has happened. Its
own colour, because inside select mode the same brackets in amber would read
as a designation about to be made.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from nuiitivet._interaction.perception import visible_rect

from .hud import FONT_SIZE, SEPARATOR, color, hud_font, paint_caption, paint_hud

logger = logging.getLogger(__name__)

# Truthy/falsy spellings accepted for the disable env var, shared with the
# action overlay so one switch turns off all dev-only drawing.
_FALSY = {"0", "false", "no", "off"}

# Amber: "the human means this", deliberately distant from the action overlay's
# indigo, and the colour annotation tools reach for.
_ACCENT = (255, 171, 0)
# Rose, for the source jump: a fourth family, since a jump is none of the other
# three -- not a note, not a report, not a change -- and the brackets it shows
# under a held chord must not read as a designation about to be made.
_JUMP_ACCENT = (236, 64, 122)
# Ink for the numbered badges.
_BADGE_INK = (32, 24, 0)

_BRACKET_LEN = 12.0
_BRACKET_WIDTH = 2.5
_BADGE_RADIUS = 10.0


def _enabled() -> bool:
    return os.environ.get("NUIITIVET_DEV_ACTION_OVERLAY", "1").strip().lower() not in _FALSY


def paint_selection(app: Any, canvas: Any, width: int, height: int) -> None:
    """Paint select-mode and source-jump feedback over the just-painted tree.

    Called from the on-screen GPU / raster frame paths *after* the widget tree is
    painted, and never from ``App._render_snapshot``, so none of this reaches
    ``screenshot``. All failures are swallowed -- a decoration must never break
    the frame.
    """
    if not _enabled():
        return
    mode = getattr(app, "_select_mode", None)
    jump = getattr(app, "_source_jump", None)
    if mode is None and jump is None:
        return
    try:
        selection = mode.selection if mode is not None else None
        active = bool(mode.active) if mode is not None else False
        marks = selection.marks() if selection is not None else []
        jump_target = jump.hovered if jump is not None else None
        jump_notice = jump.notice if jump is not None else None
        if not active and not marks and jump_target is None and not jump_notice:
            return

        from nuiitivet.rendering.skia.skia_module import get_skia

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return

        from nuiitivet.widgeting.context_lookup import find_window

        font, typeface = hud_font(skia)
        newest_index = marks[-1][0] if marks else None
        for index, kind, mark in marks:
            if kind != "region":
                # The selection is shared across windows; paint a node's mark
                # only in the window that owns it, or its rect would show as a
                # ghost at the same coordinates in every other window. An
                # unresolvable owner (a bare test tree) paints as before.
                # Regions carry no owner and still paint everywhere — a known
                # multi-window limitation.
                owner = find_window(mark)
                if owner is not None and owner is not app:
                    continue
            rect = mark if kind == "region" else visible_rect(mark)
            if rect is None:
                continue
            # While designating, only the newest mark carries full weight; once
            # committed every mark is equal and reduced to its badge.
            full = active and index == newest_index
            if kind == "region":
                # A wash rather than an outline: "this area", against a node's
                # brackets meaning "this object". Two stroked rectangles of the
                # same weight would be the unreadable case when they nest.
                _paint_wash(skia, canvas, rect, 0.22 if full else 0.13)
            elif full:
                paint_brackets(skia, canvas, rect, 1.0)
            _paint_badge(skia, canvas, rect, str(index), font, typeface, 1.0 if full else 0.75)

        if active and mode is not None and selection is not None:
            band = mode.band
            if band is not None:
                _paint_band(skia, canvas, band)
            _paint_hover(skia, canvas, mode, font, typeface, selection.members(), skip=jump_target)
            _paint_hud(skia, canvas, mode, marks, jump_notice, font, typeface, width, height)
        if jump_target is not None or jump_notice:
            # A latched mode folds the jump's notice into its own badge.
            editing = getattr(app, "_layout_edit_mode", None)
            alone = not active and not (editing is not None and editing.active)
            _paint_jump(skia, canvas, jump_target, jump_notice, font, typeface, width, height, alone=alone)
    except Exception:
        logger.debug("selection_overlay: paint failed", exc_info=True)


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
    """Fill a designated area -- "this region", as distinct from "this object"."""
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
    """Draw the numbered pin at a mark's top-left corner.

    The number is what lets the human say "the second one" and have it match the
    payload's ``index``.
    """
    x, y, _w, _h = rect
    disc = skia.Paint(AntiAlias=True)
    disc.setColor(color(skia, _ACCENT, alpha))
    canvas.drawCircle(x, y, _BADGE_RADIUS, disc)
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

    ``skip`` is the widget the source jump is already bracketing: while its
    chord is held the click is a jump, so the jump's caption is the one to show.
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


def _paint_jump(
    skia: Any,
    canvas: Any,
    target: Any,
    notice: Optional[str],
    font: Any,
    typeface: Any,
    width: int,
    height: int,
    *,
    alone: bool,
) -> None:
    """Bracket the widget a chorded click would open, and say what the last jump did.

    The notice replaces the caption rather than sitting beside it: right after
    a jump, what happened is the only thing worth reading, and the next pointer
    move clears it. With the chord already released there is no widget to hang
    it on, so it takes the badge's place -- when ``alone``; a latched mode
    carries it in its badge instead.
    """
    rect = visible_rect(target) if target is not None else None
    if rect is None:
        if notice and alone:
            paint_hud(
                skia,
                canvas,
                mode_line=None,
                hints=(),
                notices=[notice],
                placement=None,
                pointer=None,
                font=font,
                typeface=typeface,
                width=width,
                height=height,
            )
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
    """The badge while the mode is latched: the mode, its counts and exits, then the keys that apply now.

    A latched mode can be left on by accident, so it must be unmistakable that
    clicks are being taken as designations rather than reaching the app. The two
    counts stay separate for the same reason the payload keeps them apart: they
    mean different things.
    """
    regions = sum(1 for _index, kind, _mark in marks if kind == "region")
    parts = [_plural(len(marks) - regions, "widget")]
    if regions:
        parts.append(_plural(regions, "region"))

    mode_line = SEPARATOR.join(("SELECT", "designate for the assistant", *parts, mode.exit, "Ctrl+Shift+E edit"))
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
    "describe_node",
    "paint_brackets",
    "paint_selection",
]
