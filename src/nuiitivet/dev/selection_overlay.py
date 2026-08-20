"""Human-facing feedback for inspect mode (#591).

The visual half of :mod:`nuiitivet.dev.inspect`. Where
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

* *While latched* -- a HUD badge, a hover highlight on the pick candidate, the
  newest designation at full strength, and every earlier one dimmed to its badge.
  Designation is sequential, so full legibility is only ever needed for the one
  just made; this is what keeps the overlay readable as the count grows. The HUD
  names **every** gesture that leaves or unmakes a designation, because it is the
  only place a human can learn them -- there is no menu and no panel, and a key
  the badge does not mention is a key nobody finds.
* *After committing* (``Enter``) -- **numbered badges only**. The human is done
  pointing and wants to see their app again; the durable record lives in the
  payload, not on the glass. It is the numbered-pin behaviour every annotation
  tool converges on, and it also defuses the "latched mode left on obscures the
  screen" hazard.

Nodes are drawn as **corner brackets** rather than a full outline, so that when
region designation lands (the second half of #591, drawn as a faint fill) the two
read as different *classes* of mark instead of two similar rectangles.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from nuiitivet._interaction.perception import visible_rect

logger = logging.getLogger(__name__)

# Truthy/falsy spellings accepted for the disable env var, shared with the
# action overlay so one switch turns off all dev-only drawing.
_FALSY = {"0", "false", "no", "off"}

# Amber: "the human means this", deliberately distant from the action overlay's
# indigo, and the colour annotation tools reach for.
_ACCENT = (255, 171, 0)
# Ink and ground for badges and captions.
_BADGE_INK = (32, 24, 0)
_CAPTION_BG = (28, 24, 14, 220)
_CAPTION_INK = (250, 244, 230)

_BRACKET_LEN = 12.0
_BRACKET_WIDTH = 2.5
_BADGE_RADIUS = 10.0
_FONT_SIZE = 12.0
_HUD_MARGIN = 12.0


def _enabled() -> bool:
    return os.environ.get("NUIITIVET_DEV_ACTION_OVERLAY", "1").strip().lower() not in _FALSY


def _color(skia: Any, rgb: tuple[int, int, int], alpha: float) -> Any:
    r, g, b = rgb
    return skia.Color(r, g, b, max(0, min(255, int(round(alpha * 255)))))


def paint_selection(app: Any, canvas: Any, width: int, height: int) -> None:
    """Paint inspect-mode feedback over the just-painted tree.

    Called from the on-screen GPU / raster frame paths *after* the widget tree is
    painted, and never from ``App._render_snapshot``, so none of this reaches
    ``screenshot``. All failures are swallowed -- a decoration must never break
    the frame.
    """
    if not _enabled():
        return
    mode = getattr(app, "_inspect_mode", None)
    if mode is None:
        return
    try:
        selection = mode.selection
        active = bool(mode.active)
        marks = selection.marks()
        if not active and not marks:
            return

        from nuiitivet.rendering.skia.skia_module import get_skia

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return

        font, typeface = _font(skia)
        newest_index = marks[-1][0] if marks else None
        for index, kind, mark in marks:
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
                _paint_brackets(skia, canvas, rect, 1.0)
            _paint_badge(skia, canvas, rect, str(index), font, typeface, 1.0 if full else 0.75)

        if active:
            band = mode.band
            if band is not None:
                _paint_band(skia, canvas, band)
            _paint_hover(skia, canvas, mode, font, typeface, selection.members())
            _paint_hud(skia, canvas, font, typeface, marks, width, height)
    except Exception:
        logger.debug("selection_overlay: paint failed", exc_info=True)


def _font(skia: Any) -> tuple[Any, Any]:
    from nuiitivet.rendering.skia.font import (
        get_default_font_fallbacks,
        get_typeface,
        make_font,
    )

    typeface = get_typeface(family_candidates=get_default_font_fallbacks(), fallback_to_default=True)
    return (make_font(typeface, _FONT_SIZE), typeface)


def _paint_brackets(skia: Any, canvas: Any, rect: tuple[float, ...], alpha: float) -> None:
    """Draw four corner brackets -- "this object", as distinct from "this area"."""
    x, y, w, h = rect
    arm = min(_BRACKET_LEN, max(2.0, w / 3.0), max(2.0, h / 3.0))
    paint = skia.Paint(AntiAlias=True)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(_BRACKET_WIDTH)
    paint.setColor(_color(skia, _ACCENT, alpha))
    for cx, sx in ((x, 1.0), (x + w, -1.0)):
        for cy, sy in ((y, 1.0), (y + h, -1.0)):
            canvas.drawLine(cx, cy, cx + arm * sx, cy, paint)
            canvas.drawLine(cx, cy, cx, cy + arm * sy, paint)


def _paint_wash(skia: Any, canvas: Any, rect: tuple[float, ...], alpha: float) -> None:
    """Fill a designated area -- "this region", as distinct from "this object"."""
    x, y, w, h = rect
    paint = skia.Paint(AntiAlias=True)
    paint.setColor(_color(skia, _ACCENT, alpha))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint)


def _paint_band(skia: Any, canvas: Any, rect: tuple[float, ...]) -> None:
    """Draw the rect a drag has swept so far, so the human can aim before letting go."""
    x, y, w, h = rect
    _paint_wash(skia, canvas, rect, 0.18)
    stroke = skia.Paint(AntiAlias=True)
    stroke.setStyle(skia.Paint.kStroke_Style)
    stroke.setStrokeWidth(1.5)
    stroke.setColor(_color(skia, _ACCENT, 0.9))
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
    disc.setColor(_color(skia, _ACCENT, alpha))
    canvas.drawCircle(x, y, _BADGE_RADIUS, disc)
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    blob = make_text_blob(label, font)
    if blob is None:
        return
    text_w = measure_text_width(typeface, _FONT_SIZE, label)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(_color(skia, _BADGE_INK, alpha))
    canvas.drawTextBlob(blob, x - text_w / 2.0, y + _FONT_SIZE / 2.5, ink)


def _paint_hover(
    skia: Any, canvas: Any, mode: Any, font: Any, typeface: Any, members: list[Any]
) -> None:
    """Outline the pick candidate and name it, so the human can aim before clicking."""
    candidate = mode.hovered
    if candidate is None or any(candidate is member for member in members):
        return
    rect = visible_rect(candidate)
    if rect is None:
        return
    x, y, w, h = rect
    wash = skia.Paint(AntiAlias=True)
    wash.setColor(_color(skia, _ACCENT, 0.16))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), wash)
    _paint_brackets(skia, canvas, rect, 0.7)
    _caption(skia, canvas, _describe(candidate), font, typeface, x, max(0.0, y - 22.0))


def _describe(node: Any) -> str:
    """Name the candidate the way ``describe_tree`` would, for a caption."""
    from nuiitivet.dev.interaction import resolve_target

    identity = resolve_target(node)
    name = identity.get("key") or identity.get("label")
    return f"{identity.get('type', type(node).__name__)}  {name}" if name else str(
        identity.get("type", type(node).__name__)
    )


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


# Every gesture that leaves or unmakes a designation. The HUD is the only place
# a human can learn these -- there is no menu and no panel -- and leaving one out
# makes it effectively nonexistent: `Backspace` went undiscovered precisely
# because the badge never mentioned it.
_HINTS = (
    "Enter keep",
    "Esc discard",
    "Backspace remove",
    "Ctrl+Backspace clear",
)

_SEPARATOR = "  ·  "


def _wrap(parts: tuple[str, ...], typeface: Any, max_width: float) -> list[str]:
    """Greedily pack ``parts`` into lines that fit ``max_width``.

    Measured rather than split at a fixed point, because the hint has to stay
    readable in a narrow window -- a dev app is often a few hundred pixels wide,
    and a hint running off the edge teaches nothing.
    """
    from nuiitivet.rendering.skia.font import measure_text_width

    lines: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current}{_SEPARATOR}{part}" if current else part
        if current and measure_text_width(typeface, _FONT_SIZE, candidate) > max_width:
            lines.append(current)
            current = part
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _paint_hud(
    skia: Any,
    canvas: Any,
    font: Any,
    typeface: Any,
    marks: list[tuple[int, str, Any]],
    width: int,
    height: int,
) -> None:
    """A persistent badge while the mode is latched.

    A latched mode can be left on by accident, so it must be unmistakable that
    clicks are being taken as designations rather than reaching the app. The two
    counts stay separate for the same reason the payload keeps them apart: they
    mean different things.
    """
    regions = sum(1 for _index, kind, _mark in marks if kind == "region")
    parts = [_plural(len(marks) - regions, "widget")]
    if regions:
        parts.append(_plural(regions, "region"))

    lines = ["INSPECT" + _SEPARATOR + _SEPARATOR.join(parts)]
    lines.extend(_wrap(_HINTS, typeface, max(80.0, width - _HUD_MARGIN * 2 - 16.0)))
    for index, line in enumerate(lines):
        _caption(skia, canvas, line, font, typeface, _HUD_MARGIN, _HUD_MARGIN + index * 24.0)


def _caption(
    skia: Any, canvas: Any, text: str, font: Any, typeface: Any, x: float, y: float
) -> None:
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    blob = make_text_blob(text, font)
    if blob is None:
        return
    text_w = measure_text_width(typeface, _FONT_SIZE, text)
    pad, box_h = 8.0, 20.0
    bg = skia.Paint(AntiAlias=True)
    r, g, b, a = _CAPTION_BG
    bg.setColor(skia.Color(r, g, b, a))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, text_w + pad * 2, box_h), 5.0, 5.0, bg)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(_color(skia, _CAPTION_INK, 1.0))
    canvas.drawTextBlob(blob, x + pad, y + box_h - 6.0, ink)


__all__ = ["paint_selection"]
