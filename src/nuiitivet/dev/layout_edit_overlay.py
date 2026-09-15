"""Human-facing feedback for layout edit mode.

The visual half of :mod:`nuiitivet.dev.layout_edit_mode`, drawn under the same rules
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
from typing import Any, Optional

from nuiitivet._interaction.perception import global_visual_rect

from .hud import CAPTION_BG, CAPTION_INK, FONT_SIZE, SEPARATOR, color, hud_font, paint_caption, paint_hud
from .selection_overlay import _enabled as _overlays_enabled
from .selection_overlay import describe_node, paint_brackets

logger = logging.getLogger(__name__)

# Teal: distant from amber and from indigo alike.
_ACCENT = (0, 168, 160)
# Room a layer list needs beside its stack before it moves inside it.
_LAYERS_WIDTH = 220.0
_DASH = (6.0, 4.0)
# Beside the layer list, since the keys act on it; the badge does not repeat them.
_LAYER_HINT = "W/S/0-9 layer"


def paint_layout_edit(app: Any, canvas: Any, width: int, height: int) -> None:
    """Paint layout-mode feedback over the just-painted tree.

    Ghosts outlive the mode: an edit written just before leaving still needs
    its ghost until the reload lands. All failures are swallowed.
    """
    if not _overlays_enabled():
        return
    mode = getattr(app, "_layout_edit_mode", None)
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
        jump_notice = jump.notice if jump is not None else None
        if active and not mode.dragging and jump_target is None:
            _paint_candidate(skia, canvas, mode, font, typeface)
        for ghost in ghosts:
            if ghost.shape == "line":
                _paint_insertion_line(skia, canvas, ghost.rect, ghost.caption, font, typeface)
            elif ghost.shape == "wash":
                _paint_wash(skia, canvas, ghost.rect)
            elif ghost.shape == "cell":
                _paint_cell(skia, canvas, ghost.rect, ghost.caption, font, typeface)
            else:
                _paint_ghost(skia, canvas, ghost.rect, ghost.caption, font, typeface)
        layers = mode.layers if active else None
        if layers is not None:
            _paint_layers(skia, canvas, layers, font, typeface, width)
        editor = mode.editor if active else None
        if editor is not None:
            _paint_editor(skia, canvas, app, editor, font, typeface)
        if active:
            _paint_hud(skia, canvas, mode, jump_notice, font, typeface, width, height)
        elif notice:
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
    except Exception:
        logger.debug("layout_edit_overlay: paint failed", exc_info=True)


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
    _paint_tint(skia, canvas, rect, 0.10, 1.0)


def _paint_cell(skia: Any, canvas: Any, rect: tuple[float, ...], caption: str, font: Any, typeface: Any) -> None:
    """The grid cell a move will take: a deeper tint inside the grid's wash, captioned."""
    _paint_tint(skia, canvas, rect, 0.22, 2.0)
    if caption:
        paint_caption(skia, canvas, caption, font, typeface, rect[0], rect[1] + rect[3] + 4.0)


def _paint_tint(skia: Any, canvas: Any, rect: tuple[float, ...], alpha: float, edge_width: float) -> None:
    x, y, w, h = rect
    fill = skia.Paint(AntiAlias=True)
    fill.setColor(color(skia, _ACCENT, alpha))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill)
    edge = skia.Paint(AntiAlias=True)
    edge.setStyle(skia.Paint.kStroke_Style)
    edge.setStrokeWidth(edge_width)
    edge.setColor(color(skia, _ACCENT, 0.7))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), edge)


def _paint_layers(skia: Any, canvas: Any, layers: Any, font: Any, typeface: Any, width: int) -> None:
    """The stack's layers, top first, beside the stack, and the keys that pick one.

    The landing is marked and the dragged widget's own layer named.
    """
    x, y, w, _h = layers.rect
    left = x + w + 6.0
    if left + _LAYERS_WIDTH > width:
        left = x + 6.0
    lines = [(len(layers.names), "on top")]
    lines.extend((index, name) for index, name in reversed(list(enumerate(layers.names))))
    for row, (index, name) in enumerate(lines):
        mark = "▸" if index == layers.landing else " "
        label = f"{mark} {index} {name}" if index < len(layers.names) else f"{mark} + {name}"
        if index == layers.own:
            label += "  (own)"
        paint_caption(skia, canvas, label, font, typeface, left, y + row * 24.0)
    paint_caption(skia, canvas, _LAYER_HINT, font, typeface, left, y + len(lines) * 24.0)


def _paint_editor(skia: Any, canvas: Any, app: Any, editor: Any, font: Any, typeface: Any) -> None:
    """The field over the widget's text: its box, the selection, the text, the composition's underline, the caret.

    The caret's rect goes to the window's IME state the way a text field's
    does, so the candidate window opens beside it and not in a corner.
    """
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    x, y, w, h = editor.rect
    pad = 8.0
    value = editor.value
    text, selection = value.text, value.selection

    def at(index: int) -> float:
        return x + pad + measure_text_width(typeface, FONT_SIZE, text[:index])

    box_w = max(w, measure_text_width(typeface, FONT_SIZE, text) + pad * 2)
    box_h = max(h, 24.0)
    fill = skia.Paint(AntiAlias=True)
    fill.setColor(skia.Color(*CAPTION_BG))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box_w, box_h), 5.0, 5.0, fill)
    edge = skia.Paint(AntiAlias=True)
    edge.setStyle(skia.Paint.kStroke_Style)
    edge.setStrokeWidth(2.0)
    edge.setColor(color(skia, _ACCENT, 0.95))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box_w, box_h), 5.0, 5.0, edge)
    if not selection.is_collapsed:
        highlight = skia.Paint(AntiAlias=True)
        highlight.setColor(color(skia, _ACCENT, 0.3))
        left, right = at(selection.min), at(selection.max)
        canvas.drawRect(skia.Rect.MakeXYWH(left, y + 4.0, right - left, box_h - 8.0), highlight)
    baseline = y + box_h / 2.0 + FONT_SIZE / 2.5
    blob = make_text_blob(text, font)
    if blob is not None:
        ink = skia.Paint(AntiAlias=True)
        ink.setColor(color(skia, CAPTION_INK, 1.0))
        canvas.drawTextBlob(blob, x + pad, baseline, ink)
    stroke = skia.Paint(AntiAlias=True)
    stroke.setStrokeWidth(1.5)
    stroke.setColor(color(skia, _ACCENT, 1.0))
    if value.is_composing:
        canvas.drawLine(at(value.composing.min), baseline + 3.0, at(value.composing.max), baseline + 3.0, stroke)
    caret_x = at(selection.end)
    if selection.is_collapsed:
        canvas.drawLine(caret_x, y + 4.0, caret_x, y + box_h - 4.0, stroke)
    ime = getattr(app, "ime", None)
    if ime is not None:
        ime.update_cursor_rect(caret_x, y + 4.0, 2.0, box_h - 8.0)


def _paint_hud(
    skia: Any, canvas: Any, mode: Any, jump_notice: Optional[str], font: Any, typeface: Any, width: int, height: int
) -> None:
    """The badge that says a release will change the file, with the keys that apply now."""
    mode_line = SEPARATOR.join(("LAYOUT EDIT", "release writes the source", mode.exit, "Ctrl+Shift+D designate"))
    paint_hud(
        skia,
        canvas,
        mode_line=mode_line,
        hints=mode.hints,
        notices=[mode.notice, jump_notice],
        placement=mode.placement,
        pointer=mode.pointer,
        font=font,
        typeface=typeface,
        width=width,
        height=height,
    )


__all__ = ["paint_layout_edit"]
