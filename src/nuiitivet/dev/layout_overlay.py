"""Human-facing feedback for layout mode.

The visual half of :mod:`nuiitivet.dev.layout_mode`, drawn under the same rules
as :mod:`.selection_overlay`: from the live frame paths only, never from
``App._render_snapshot``, and as a pure function of the mode's state read at
paint time.

Its colour is a third family. Select mode's amber is a note the human wrote,
the action overlay's indigo is a report of what the assistant did, and this
teal is a change about to be made -- the one of the three that alters a file
on release, which is why it must never be mistaken for either of the others.
"""

from __future__ import annotations

import logging
from typing import Any

from nuiitivet._interaction.perception import global_visual_rect

from .selection_overlay import (
    _HUD_MARGIN,
    _SEPARATOR,
    color,
    describe_node,
    hud_font,
    paint_brackets,
    paint_caption,
    wrap_hints,
)
from .selection_overlay import _enabled as _overlays_enabled

logger = logging.getLogger(__name__)

# Teal: distant from amber and from indigo alike.
_ACCENT = (0, 168, 160)
_DASH = (6.0, 4.0)

# Every gesture the mode binds. The badge is the only place a human can learn
# them, so an omission hides the gesture completely.
_HINTS = (
    "drag a corner resize",
    "drag reorder / move",
    "click select",
    "↑/↓ parent/child",
    "Alt no snap",
    "Ctrl+Z undo",
    "Esc leave",
    "Ctrl+Shift+C select mode",
    "Ctrl+Shift+Click source",
)


def paint_layout(app: Any, canvas: Any, width: int, height: int) -> None:
    """Paint layout-mode feedback over the just-painted tree.

    Ghosts outlive the mode: an edit written just before leaving still needs
    its ghost until the reload lands. All failures are swallowed.
    """
    if not _overlays_enabled():
        return
    mode = getattr(app, "_layout_mode", None)
    if mode is None:
        return
    try:
        active = bool(mode.active)
        ghosts = mode.ghosts
        notice = mode.notice
        if not active and not ghosts and not notice:
            return

        from nuiitivet.rendering.skia.skia_module import get_skia

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return
        font, typeface = hud_font(skia)

        # While the source jump's chord is held the click is a jump, so its
        # brackets are the ones to show; painting the candidate's wash over
        # them would turn them grey.
        jump = getattr(app, "_source_jump", None)
        jump_target = jump.hovered if jump is not None else None
        if active and not mode.dragging and jump_target is None:
            _paint_candidate(skia, canvas, mode, font, typeface)
        for ghost in ghosts:
            if ghost.shape == "line":
                _paint_insertion_line(skia, canvas, ghost.rect, ghost.caption, font, typeface)
            elif ghost.shape == "wash":
                _paint_wash(skia, canvas, ghost.rect)
            else:
                _paint_ghost(skia, canvas, ghost.rect, ghost.caption, font, typeface)
        if active:
            _paint_hud(skia, canvas, font, typeface, width)
        if notice:
            paint_caption(skia, canvas, notice, font, typeface, _HUD_MARGIN, height - _HUD_MARGIN - 20.0)
    except Exception:
        logger.debug("layout_overlay: paint failed", exc_info=True)


def _paint_candidate(skia: Any, canvas: Any, mode: Any, font: Any, typeface: Any) -> None:
    """Bracket the widget a corner drag would resize, and name it.

    The brackets are the grab zones: a press on one starts the drag.
    """
    candidate = mode.candidate
    if candidate is None:
        return
    rect = global_visual_rect(candidate)
    if rect is None:
        return
    x, y, w, h = rect
    wash = skia.Paint(AntiAlias=True)
    wash.setColor(color(skia, _ACCENT, 0.12 if candidate is mode.selected else 0.08))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), wash)
    paint_brackets(skia, canvas, rect, 1.0 if candidate is mode.selected else 0.8, _ACCENT)
    paint_caption(skia, canvas, describe_node(candidate), font, typeface, x, max(0.0, y - 22.0))


def _paint_ghost(skia: Any, canvas: Any, rect: tuple[float, ...], caption: str, font: Any, typeface: Any) -> None:
    """The dashed outline of what the edit will produce, captioned with its value."""
    x, y, w, h = rect
    stroke = skia.Paint(AntiAlias=True)
    stroke.setStyle(skia.Paint.kStroke_Style)
    stroke.setStrokeWidth(2.0)
    stroke.setColor(color(skia, _ACCENT, 0.95))
    stroke.setPathEffect(skia.DashPathEffect.Make(list(_DASH), 0.0))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), stroke)
    if caption:
        paint_caption(skia, canvas, caption, font, typeface, x, y + h + 4.0)


def _paint_insertion_line(
    skia: Any, canvas: Any, rect: tuple[float, ...], caption: str, font: Any, typeface: Any
) -> None:
    """The slot a reorder will land in: a solid line across the gap, captioned."""
    x, y, w, h = rect
    stroke = skia.Paint(AntiAlias=True)
    stroke.setStyle(skia.Paint.kStroke_Style)
    stroke.setStrokeWidth(3.0)
    stroke.setStrokeCap(skia.Paint.kRound_Cap)
    stroke.setColor(color(skia, _ACCENT, 0.95))
    canvas.drawLine(x, y, x + w, y + h, stroke)
    if caption:
        paint_caption(skia, canvas, caption, font, typeface, x, y + h + 4.0)


def _paint_wash(skia: Any, canvas: Any, rect: tuple[float, ...]) -> None:
    """The container a move will land in: a tint with a thin solid edge."""
    x, y, w, h = rect
    fill = skia.Paint(AntiAlias=True)
    fill.setColor(color(skia, _ACCENT, 0.10))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill)
    edge = skia.Paint(AntiAlias=True)
    edge.setStyle(skia.Paint.kStroke_Style)
    edge.setStrokeWidth(1.0)
    edge.setColor(color(skia, _ACCENT, 0.7))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), edge)


def _paint_hud(skia: Any, canvas: Any, font: Any, typeface: Any, width: int) -> None:
    """The badge that says a release will change the file."""
    lines = ["LAYOUT" + _SEPARATOR + "release writes the source"]
    lines.extend(wrap_hints(_HINTS, typeface, max(80.0, width - _HUD_MARGIN * 2 - 16.0)))
    for index, line in enumerate(lines):
        paint_caption(skia, canvas, line, font, typeface, _HUD_MARGIN, _HUD_MARGIN + index * 24.0)


__all__ = ["paint_layout"]
