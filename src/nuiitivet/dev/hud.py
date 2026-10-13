"""What the dev modes draw to say where they are: the splash, the help sheet, the notices and the captions.

On entering a mode a line at the window's centre names it and the key that
opens the help, and on leaving says how it was left, each for a few seconds.
The help sheet lists every gesture of the mode while ``H`` is held. A notice sits in a box at the
bottom-left that steps out of the pointer's way and comes back only once the
pointer is well clear.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from nuiitivet.observable import runtime

logger = logging.getLogger(__name__)

#: Between the parts of a caption or a hint line. ASCII on purpose: the
#: overlay draws with the platform's UI font, and a middle dot is missing from
#: macOS's, which paints it as a box.
SEPARATOR = "  |  "

FONT_SIZE = 12.0
MARGIN = 12.0
# Ink and ground for captions and the badge.
CAPTION_BG = (28, 24, 14, 220)
CAPTION_INK = (250, 244, 230)

PAD = 8.0
LINE_HEIGHT = 20.0
_RADIUS = 5.0
# The pointer this close to the badge moves it; only this far from the badge's
# home brings it back. The gap between the two is what keeps it from flickering.
_DODGE = 40.0
_RETURN = 120.0

# Seconds the splash stays after a mode is entered or left: long enough to find and read the line.
SPLASH = 3.0
# Between the key column of the help sheet and what each key does.
_GUTTER = 24.0
# The icon font the badges' answer glyphs come from: the one the Icon widget draws by default.
_SYMBOLS_FILE = "MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf"

Point = tuple[float, float]
Size = tuple[float, float]

_now = time.monotonic


class Splash:
    """A line at the window's centre for ``SPLASH`` seconds, as a mode is entered or left. One per mode."""

    def __init__(self) -> None:
        self._since: Optional[float] = None
        self._text = ""
        # Which ``show`` the armed frame belongs to; an older one must not end a newer splash.
        self._serial = 0

    def show(self, app: Any, text: str) -> None:
        """Show ``text`` from now and arm the frame that takes it away."""
        self._since = _now()
        self._text = text
        self._serial += 1
        serial = self._serial

        def hide(_dt: float) -> None:
            # Ends the splash itself: the clock may fire a hair before the time comparison agrees.
            if serial != self._serial:
                return
            self._since = None
            try:
                app.invalidate(content=False)
            except Exception:
                logger.debug("hud: failed to repaint after the splash", exc_info=True)

        try:
            runtime.get_clock().schedule_once(hide, SPLASH)
        except Exception:
            logger.debug("hud: failed to schedule the splash's end", exc_info=True)

    @property
    def text(self) -> Optional[str]:
        """The line a frame painted now shows, or ``None`` once it is gone."""
        if self._since is not None and _now() - self._since < SPLASH:
            return self._text
        return None


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


def fit_inside(at: Point, box: Size, window: Size) -> Point:
    """``at`` moved the least distance that puts a ``box`` there inside the window's margins.

    A box wider or taller than the window sits at the top-left margin.
    """
    x = min(max(MARGIN, at[0]), max(MARGIN, window[0] - MARGIN - box[0]))
    y = min(max(MARGIN, at[1]), max(MARGIN, window[1] - MARGIN - box[1]))
    return (x, y)


def caption_size(text: str, typeface: Any) -> Size:
    """The box ``paint_caption`` draws for ``text``: as wide as its longest line, a row per ``'\\n'``."""
    from nuiitivet.rendering.skia.font import measure_text_width

    lines = text.split("\n")
    widest = max(measure_text_width(typeface, FONT_SIZE, line) for line in lines)
    return (widest + PAD * 2, LINE_HEIGHT * len(lines))


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


# The Material Symbols typeface, read from the package once; ``False`` once a read failed.
_symbols: Any = None


def symbol_font(size: float) -> tuple[Any, Any]:
    """The packaged Material Symbols ``(font, typeface)`` at ``size``; ``(None, None)`` when it cannot be read."""
    global _symbols
    if _symbols is None:
        try:
            import importlib.resources as resources

            from nuiitivet.rendering.skia.font import typeface_from_bytes

            data = resources.files("nuiitivet.material").joinpath("symbols").joinpath(_SYMBOLS_FILE).read_bytes()
            _symbols = typeface_from_bytes(data) or False
        except Exception:
            logger.debug("hud: the symbols font could not be read", exc_info=True)
            _symbols = False
    if not _symbols:
        return (None, None)
    from nuiitivet.rendering.skia.font import make_font

    return (make_font(_symbols, size), _symbols)


def color(skia: Any, rgb: tuple[int, int, int], alpha: float) -> Any:
    """A skia colour from an RGB triple and a 0..1 alpha."""
    r, g, b = rgb
    return skia.Color(r, g, b, max(0, min(255, int(round(alpha * 255)))))


def paint_hud(
    skia: Any,
    canvas: Any,
    *,
    notices: list[Optional[str]],
    placement: Optional[Placement],
    pointer: Optional[Point],
    font: Any,
    typeface: Any,
    width: float,
    height: float,
) -> None:
    """Draw the notices, a line each, in one box at the bottom-left; nothing with none to draw.

    Without a ``placement`` the box sits at home, which is what a notice
    outliving its mode gets.
    """
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    lines = [notice for notice in notices if notice]
    if not lines:
        return
    text_w = max(measure_text_width(typeface, FONT_SIZE, line) for line in lines)
    box: Size = (text_w + PAD * 2, len(lines) * LINE_HEIGHT + 4.0)
    x, y = (placement or Placement()).place(box, (width, height), pointer)
    _paint_box(skia, canvas, x, y, box)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))
    for index, line in enumerate(lines):
        blob = make_text_blob(line, font)
        if blob is not None:
            canvas.drawTextBlob(blob, x + PAD, y + 2.0 + (index + 1) * LINE_HEIGHT - 6.0, ink)


def paint_splash(skia: Any, canvas: Any, text: str, font: Any, typeface: Any, width: float, height: float) -> None:
    """Draw ``text`` in a caption box at the window's centre."""
    if font is None:
        return
    box = caption_size(text, typeface)
    x, y = fit_inside(((width - box[0]) / 2.0, (height - box[1]) / 2.0), box, (width, height))
    paint_caption(skia, canvas, text, font, typeface, x, y)


def paint_caption(
    skia: Any,
    canvas: Any,
    text: str,
    font: Any,
    typeface: Any,
    x: float,
    y: float,
    window: Optional[Size] = None,
) -> None:
    """A caption in a dark rounded box with its top-left at ``(x, y)``, a row per ``'\\n'``.

    Given the ``window``, the box is pushed inside its margins first.
    """
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob

    box = caption_size(text, typeface)
    if window is not None:
        x, y = fit_inside((x, y), box, window)
    _paint_box(skia, canvas, x, y, box)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))
    for row, line in enumerate(text.split("\n")):
        blob = make_text_blob(line, font)
        if blob is not None:
            canvas.drawTextBlob(blob, x + PAD, y + (row + 1) * LINE_HEIGHT - 6.0, ink)


def paint_sheet(
    skia: Any,
    canvas: Any,
    title: str,
    rows: tuple[tuple[str, str], ...],
    font: Any,
    typeface: Any,
    width: float,
    height: float,
) -> None:
    """Draw ``title`` and every ``(key, what)`` row in one box at the window's centre."""
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    def measure(text: str) -> float:
        return float(measure_text_width(typeface, FONT_SIZE, text))

    key_w = max(measure(key) for key, _what in rows)
    what_w = max(measure(what) for _key, what in rows)
    box: Size = (max(measure(title), key_w + _GUTTER + what_w) + PAD * 2, (len(rows) + 1) * LINE_HEIGHT + PAD * 2)
    x, y = fit_inside(((width - box[0]) / 2.0, (height - box[1]) / 2.0), box, (width, height))
    _paint_box(skia, canvas, x, y, box)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))

    def draw(text: str, at: float, row: int) -> None:
        blob = make_text_blob(text, font)
        if blob is not None:
            canvas.drawTextBlob(blob, at, y + PAD + (row + 1) * LINE_HEIGHT - 6.0, ink)

    draw(title, x + PAD, 0)
    for row, (key, what) in enumerate(rows, start=1):
        draw(key, x + PAD, row)
        draw(what, x + PAD + key_w + _GUTTER, row)


#: A row of a thread: the icon glyph that leads it, or ``None`` on a continuation row, and its text.
Row = tuple[Optional[str], str]
#: The column the row icons take, left of the text.
ICON_GUTTER = 20.0
_ICON_SIZE = 14.0


def rows_size(rows: list[Row], typeface: Any) -> Size:
    """The box ``paint_rows`` draws for ``rows``: the icon column plus the widest text, a row each."""
    from nuiitivet.rendering.skia.font import measure_text_width

    widest = max(measure_text_width(typeface, FONT_SIZE, text) for _icon, text in rows)
    return (ICON_GUTTER + widest + PAD * 2, LINE_HEIGHT * len(rows))


def paint_rows(skia: Any, canvas: Any, rows: list[Row], font: Any, typeface: Any, x: float, y: float) -> None:
    """A dark rounded box with its top-left at ``(x, y)``, a row each, the icon in a column left of the text."""
    if font is None:
        return
    from nuiitivet.rendering.skia.font import make_text_blob

    _paint_box(skia, canvas, x, y, rows_size(rows, typeface))
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))
    icon_font, _icon_typeface = symbol_font(_ICON_SIZE)
    for row, (icon, text) in enumerate(rows):
        top = y + row * LINE_HEIGHT
        if icon is not None and icon_font is not None:
            blob = make_text_blob(icon, icon_font)
            if blob is not None:
                # An icon glyph stands on the baseline and rises its size; centred on the row.
                canvas.drawTextBlob(blob, x + PAD, top + (LINE_HEIGHT + _ICON_SIZE) / 2.0, ink)
        blob = make_text_blob(text, font)
        if blob is not None:
            canvas.drawTextBlob(blob, x + PAD + ICON_GUTTER, top + LINE_HEIGHT - 6.0, ink)


def _paint_box(skia: Any, canvas: Any, x: float, y: float, box: Size) -> None:
    bg = skia.Paint(AntiAlias=True)
    r, g, b, a = CAPTION_BG
    bg.setColor(skia.Color(r, g, b, a))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box[0], box[1]), _RADIUS, _RADIUS, bg)


__all__ = [
    "CAPTION_BG",
    "CAPTION_INK",
    "FONT_SIZE",
    "ICON_GUTTER",
    "LINE_HEIGHT",
    "MARGIN",
    "PAD",
    "SEPARATOR",
    "SPLASH",
    "Placement",
    "Row",
    "Splash",
    "caption_size",
    "color",
    "fit_inside",
    "hud_font",
    "paint_caption",
    "paint_hud",
    "paint_rows",
    "paint_sheet",
    "paint_splash",
    "rows_size",
    "symbol_font",
]
