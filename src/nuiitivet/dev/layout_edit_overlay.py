"""Layout edit mode's feedback on the glass.

Drawn under :mod:`.comment_overlay`'s rules: from the live frame paths only,
never into the widget tree, as a pure function of the mode's state read at
paint time. Teal, the colour of a change about to be written to a file.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from nuiitivet._interaction.perception import global_visual_rect

from . import toolbar
from .hud import (
    CAPTION_BG,
    CAPTION_INK,
    FONT_SIZE,
    color,
    hud_font,
    paint_caption,
    paint_hud,
    paint_sheet,
    paint_splash,
)
from .inline_field import measure, paint_field
from .comment_overlay import _enabled as _overlays_enabled
from .comment_overlay import paint_brackets

logger = logging.getLogger(__name__)

# Teal: distant from amber and from indigo alike. The spacing handles share
# it: an outlined pill is told from a bracket by its shape, not its colour.
_ACCENT = (0, 168, 160)
# Room a layer list or a pick list needs beside its widget before it moves inside it.
_LAYERS_WIDTH = 220.0
_DASH = (6.0, 4.0)
# Beside the layer list, since the keys act on it; the badge does not repeat them.
_LAYER_HINT = "W/S/0-9 layer"
#: Every gesture of the mode, for the sheet ``H`` holds open.
HELP: tuple[tuple[str, str], ...] = (
    ("Esc", "drop the selection; with none, leave"),
    ("Esc (while dragging)", "cancel the drag"),
    ("Click", "select the widget"),
    ("Drag a corner", "resize; WASD nudge a pixel, Alt skips the snap"),
    ("Drag the body", "reorder, move, or align"),
    ("Drag a spacing handle", "change the padding or gap; Alt skips the snap"),
    ("Click a spacing handle", "how many sides move with it: every side, its pair, or itself alone"),
    ("W / S", "select the parent / child"),
    ("W / S / 0-9 over a Stack", "pick the layer it lands in"),
    ("Enter (on the selection)", "edit its text"),
    ("The bar over the selection", "its style, size or type scale; a box opens its list"),
    ("Delete / Backspace", "remove the selected widget from the source"),
    ("Ctrl+Z / Ctrl+Shift+Z", "undo / redo"),
)


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
        splash = mode.splash
        if not active and not ghosts and not notice and not splash:
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
        window = (float(width), float(height))
        if active and not mode.dragging and jump_target is None:
            _paint_candidate(skia, canvas, mode, font, typeface, window)
        for ghost in ghosts:
            if ghost.shape == "line":
                _paint_insertion_line(skia, canvas, ghost.rect, ghost.caption, font, typeface)
            elif ghost.shape == "wash":
                _paint_wash(skia, canvas, ghost.rect)
            elif ghost.shape == "band":
                _paint_band(skia, canvas, ghost.rect, ghost.caption, font, typeface)
            elif ghost.shape == "cell":
                _paint_cell(skia, canvas, ghost.rect, ghost.caption, font, typeface)
            else:
                _paint_ghost(skia, canvas, ghost.rect, ghost.caption, font, typeface)
        if active and jump_target is None:
            _paint_handles(skia, canvas, mode)
        layers = mode.layers if active else None
        if layers is not None:
            _paint_layers(skia, canvas, layers, font, typeface, width)
        bar = mode.toolbar if active else None
        if bar is not None:
            _paint_toolbar(skia, canvas, bar, font, typeface, window)
        editor = mode.editor if active else None
        if editor is not None:
            paint_field(skia, canvas, app, editor.slot, editor.value, _ACCENT, font, typeface, window)
        if active:
            _paint_hud(skia, canvas, mode, jump_notice, font, typeface, width, height)
            if mode.help:
                paint_sheet(skia, canvas, "LAYOUT EDIT MODE", HELP, font, typeface, *window)
        elif notice:
            paint_hud(
                skia,
                canvas,
                notices=[notice],
                placement=None,
                pointer=None,
                font=font,
                typeface=typeface,
                width=width,
                height=height,
            )
        if splash:
            paint_splash(skia, canvas, splash, font, typeface, *window)
    except Exception:
        logger.debug("layout_edit_overlay: paint failed", exc_info=True)


def _paint_candidate(
    skia: Any, canvas: Any, mode: Any, font: Any, typeface: Any, window: tuple[float, float]
) -> None:
    """Bracket the widget a corner drag would resize, and name it.

    The brackets are the grab zones: a press on one starts the drag.
    """
    candidate, selected = mode.candidate, mode.selected
    if selected is not None and selected is not candidate:
        # The selection the pointer has left: still the toolbar's, and
        # ``Enter``'s, so it keeps a faint mark.
        kept = global_visual_rect(selected)
        if kept is not None:
            paint_brackets(skia, canvas, kept, 0.35, _ACCENT)
    if candidate is None:
        return
    rect = global_visual_rect(candidate)
    if rect is None:
        return
    x, y, w, h = rect
    wash = skia.Paint(AntiAlias=True)
    wash.setColor(color(skia, _ACCENT, 0.12 if candidate is selected else 0.08))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), wash)
    paint_brackets(skia, canvas, rect, 1.0 if candidate is selected else 0.8, _ACCENT)
    if candidate is selected and mode.toolbar is not None:
        # The bar over the selection leads with its name; a caption there
        # would say it twice.
        return
    paint_caption(skia, canvas, mode.caption or "", font, typeface, x, y - 22.0, window)


def _paint_handles(skia: Any, canvas: Any, mode: Any) -> None:
    """The spacing handles on the selection, and the band the one under the pointer would change.

    The handles are the grab zones; the band is drawn only while a handle
    is hovered, so the spacing stays invisible until the human reaches for
    it. A held handle stays, riding on its band's far edge.
    """
    hovered = mode.handle
    if hovered is not None:
        _handle, bands = hovered
        for band in bands:
            _paint_band(skia, canvas, band, "", None, None)
    for handle in mode.handles:
        x, y, w, h = handle.rect
        paint = skia.Paint(AntiAlias=True)
        paint.setColor(color(skia, _ACCENT, 1.0 if handle.filled else 0.85))
        if not handle.filled:
            # Outlined at rest: something to take hold of. Filled under the
            # pointer, with every handle that moves along: what a drag moves.
            paint.setStyle(skia.Paint.kStroke_Style)
            paint.setStrokeWidth(1.5)
        radius = min(w, h) / 2.0
        canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, h), radius, radius, paint)


def _paint_band(skia: Any, canvas: Any, rect: tuple[float, ...], caption: str, font: Any, typeface: Any) -> None:
    """The spacing a handle stands for: a tint from the content's edge to the handle, captioned with the value."""
    x, y, w, h = rect
    band = skia.Paint(AntiAlias=True)
    band.setColor(color(skia, _ACCENT, 0.18))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), band)
    if caption:
        paint_caption(skia, canvas, caption, font, typeface, x, y + h + 4.0)


def _paint_toolbar(skia: Any, canvas: Any, bar: Any, font: Any, typeface: Any, window: tuple[float, float]) -> None:
    """The bar over the selection: its name, a box per preset it takes, and the list open under one of them.

    The geometry is :mod:`.toolbar`'s, so a click lands where the box is drawn.
    """
    from nuiitivet.rendering.skia.font import make_text_blob

    if font is None:
        return
    fill = skia.Paint(AntiAlias=True)
    fill.setColor(skia.Color(*CAPTION_BG))
    bx, by, bw, bh = toolbar.backdrop(bar, measure, window)
    canvas.drawRoundRect(skia.Rect.MakeXYWH(bx, by, bw, bh), 5.0, 5.0, fill)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))
    edge = skia.Paint(AntiAlias=True)
    edge.setStyle(skia.Paint.kStroke_Style)
    edge.setStrokeWidth(1.5)
    edge.setColor(color(skia, _ACCENT, 0.95))
    wash = skia.Paint(AntiAlias=True)
    wash.setColor(color(skia, _ACCENT, 0.3))

    def text_at(text: str, x: float, y: float, h: float, pad: float = toolbar.BOX_PAD) -> None:
        blob = make_text_blob(text, font)
        if blob is not None:
            canvas.drawTextBlob(blob, x + pad, y + h / 2.0 + FONT_SIZE / 2.5, ink)

    nx, ny, _nw, nh = toolbar.name_rect(bar, measure, window)
    text_at(bar.name, nx, ny, nh, 0.0)
    for index, (box, rect) in enumerate(zip(bar.boxes, toolbar.box_rects(bar, measure, window))):
        x, y, w, h = rect
        if index == bar.open:
            canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, h), 5.0, 5.0, wash)
        canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, h), 5.0, 5.0, edge)
        text_at(box.text, x, y, h)
    if bar.open is None:
        return
    rows = toolbar.row_rects(bar, measure, window)
    if not rows:
        return
    x, y, w, _h = rows[0]
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, toolbar.ROW_H * len(rows)), 5.0, 5.0, fill)
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, toolbar.ROW_H * len(rows)), 5.0, 5.0, edge)
    box = bar.boxes[bar.open]
    for index, (option, rect) in enumerate(zip(box.options, rows)):
        x, y, w, h = rect
        if index == bar.highlighted:
            canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), wash)
        text_at(f"{'•' if index == box.current else ' '} {option}", x, y, h)


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


def _paint_hud(
    skia: Any, canvas: Any, mode: Any, jump_notice: Optional[str], font: Any, typeface: Any, width: int, height: int
) -> None:
    """The box at the bottom-left while latched: the mode's notice and the jump's, when there are any."""
    paint_hud(
        skia,
        canvas,
        notices=[mode.notice, jump_notice],
        placement=mode.placement,
        pointer=mode.pointer,
        font=font,
        typeface=typeface,
        width=width,
        height=height,
    )


__all__ = ["paint_layout_edit"]
