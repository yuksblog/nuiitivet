"""The badge the dev modes share: what it is made of, where it sits, and how it is drawn.

One box, at the bottom-left where app content is thinnest. Its first line
names the mode and its exits and never goes away, since a latched mode must be
unmistakable; the hint line below lists only the keys that mean something at
this moment, so each key appears exactly when pressing it would do something;
a notice, when there is one, is the last line. The box steps out of the
pointer's way rather than hiding, and comes back only once the pointer is well
clear, so it never flickers.
"""

from __future__ import annotations

from typing import Any, Optional

#: Between the parts of a caption or a hint line. ASCII on purpose: the
#: overlay draws with the platform's UI font, and a middle dot is missing from
#: macOS's, which paints it as a box.
SEPARATOR = "  |  "

FONT_SIZE = 12.0
MARGIN = 12.0
# Ink and ground for captions and the badge.
CAPTION_BG = (28, 24, 14, 220)
CAPTION_INK = (250, 244, 230)

_PAD = 8.0
_LINE_HEIGHT = 20.0
_RADIUS = 5.0
# The pointer this close to the badge moves it; only this far from the badge's
# home brings it back. The gap between the two is what keeps it from flickering.
_DODGE = 40.0
_RETURN = 120.0

Point = tuple[float, float]
Size = tuple[float, float]


class Placement:
    """Where the badge sits: at home in the bottom-left, or out of the pointer's way.

    A box narrower than half the window steps across to the right; a wider one
    gains nothing from that and goes to the top instead. Once away it stays
    until the pointer is well clear of home. One per mode, kept across frames.
    """

    def __init__(self) -> None:
        self.away = False
        # The home rect of the last frame drawn, so a pointer move can be
        # judged between frames without knowing what the next box will hold.
        self._home: Optional[tuple[float, float, float, float]] = None

    def reset(self) -> None:
        """Back home, as a mode entering starts."""
        self.away = False
        self._home = None

    def place(self, box: Size, window: Size, pointer: Optional[Point]) -> Point:
        """The box's top-left for this frame, given its size, the window's, and the pointer."""
        width, height = window
        box_w, box_h = box
        home = (MARGIN, max(MARGIN, height - MARGIN - box_h))
        self._home = (*home, box_w, box_h)
        if pointer is None:
            return home
        self.away = _near(pointer, home, box, _RETURN if self.away else _DODGE)
        if not self.away:
            return home
        if box_w < width / 2.0:
            return (max(MARGIN, width - MARGIN - box_w), home[1])
        return (MARGIN, MARGIN)

    def crosses(self, pointer: Point) -> bool:
        """Whether a pointer now at ``pointer`` would move the box from where it was last drawn.

        What a mode asks on a pointer move to know if a frame is due: it
        repaints only when the hover changes, and the box has to move even
        when the hover does not.
        """
        if self._home is None:
            return False
        x, y, w, h = self._home
        return _near(pointer, (x, y), (w, h), _RETURN if self.away else _DODGE) != self.away


def _near(pointer: Point, origin: Point, box: Size, margin: float) -> bool:
    px, py = pointer
    x, y = origin
    w, h = box
    return x - margin <= px <= x + w + margin and y - margin <= py <= y + h + margin


def hud_font(skia: Any) -> tuple[Any, Any]:
    """The overlay's ``(font, typeface)`` at the HUD size."""
    from nuiitivet.rendering.skia.font import (
        get_default_font_fallbacks,
        get_typeface,
        make_font,
    )

    typeface = get_typeface(family_candidates=get_default_font_fallbacks(), fallback_to_default=True)
    return (make_font(typeface, FONT_SIZE), typeface)


def color(skia: Any, rgb: tuple[int, int, int], alpha: float) -> Any:
    """A skia colour from an RGB triple and a 0..1 alpha."""
    r, g, b = rgb
    return skia.Color(r, g, b, max(0, min(255, int(round(alpha * 255)))))


def wrap_hints(parts: tuple[str, ...], typeface: Any, max_width: float) -> list[str]:
    """Greedily pack ``parts`` into lines that fit ``max_width``.

    Measured rather than split at a fixed point, because the hint has to stay
    readable in a narrow window -- a dev app is often a few hundred pixels wide,
    and a hint running off the edge teaches nothing.
    """
    from nuiitivet.rendering.skia.font import measure_text_width

    lines: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current}{SEPARATOR}{part}" if current else part
        if current and measure_text_width(typeface, FONT_SIZE, candidate) > max_width:
            lines.append(current)
            current = part
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def paint_hud(
    skia: Any,
    canvas: Any,
    *,
    mode_line: Optional[str],
    hints: tuple[str, ...],
    notices: list[Optional[str]],
    placement: Optional[Placement],
    pointer: Optional[Point],
    font: Any,
    typeface: Any,
    width: float,
    height: float,
) -> None:
    """Draw the badge: the mode line, the wrapped hints, then the notices, in one box.

    Without a ``placement`` the box sits at home, which is what a notice
    outliving its mode gets.
    """
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    lines = [mode_line] if mode_line else []
    lines.extend(wrap_hints(hints, typeface, max(80.0, width - MARGIN * 2 - _PAD * 2)))
    lines.extend(notice for notice in notices if notice)
    if not lines:
        return
    text_w = max(measure_text_width(typeface, FONT_SIZE, line) for line in lines)
    box: Size = (text_w + _PAD * 2, len(lines) * _LINE_HEIGHT + 4.0)
    x, y = (placement or Placement()).place(box, (width, height), pointer)
    _paint_box(skia, canvas, x, y, box)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))
    for index, line in enumerate(lines):
        blob = make_text_blob(line, font)
        if blob is not None:
            canvas.drawTextBlob(blob, x + _PAD, y + 2.0 + (index + 1) * _LINE_HEIGHT - 6.0, ink)


def paint_caption(skia: Any, canvas: Any, text: str, font: Any, typeface: Any, x: float, y: float) -> None:
    """A one-line caption in a dark rounded box with its top-left at ``(x, y)``."""
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    blob = make_text_blob(text, font)
    if blob is None:
        return
    text_w = measure_text_width(typeface, FONT_SIZE, text)
    _paint_box(skia, canvas, x, y, (text_w + _PAD * 2, _LINE_HEIGHT))
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))
    canvas.drawTextBlob(blob, x + _PAD, y + _LINE_HEIGHT - 6.0, ink)


def _paint_box(skia: Any, canvas: Any, x: float, y: float, box: Size) -> None:
    bg = skia.Paint(AntiAlias=True)
    r, g, b, a = CAPTION_BG
    bg.setColor(skia.Color(r, g, b, a))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box[0], box[1]), _RADIUS, _RADIUS, bg)


__all__ = [
    "CAPTION_BG",
    "CAPTION_INK",
    "FONT_SIZE",
    "MARGIN",
    "SEPARATOR",
    "Placement",
    "color",
    "hud_font",
    "paint_caption",
    "paint_hud",
    "wrap_hints",
]
