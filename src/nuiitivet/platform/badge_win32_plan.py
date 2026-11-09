"""The platform-free half of the Windows badge backend.

What the overlay icon's text and pixels will be, computed without a Win32
call, so it runs and is tested on every platform. ``badge_win32`` turns the
pixels into an ``HICON``.
"""

from __future__ import annotations

from typing import Any

from nuiitivet.rendering.skia import get_skia

_MAX_COUNT = 99
_MAX_TEXT_LENGTH = 3

_FILL = 0xFFD93025
_TEXT = 0xFFFFFFFF

# Shares of the icon's edge: the first font size tried, and the widest the text may be.
_FONT_SHARE = 0.72
_TEXT_SHARE = 0.84
_MIN_FONT_SIZE = 4.0


def overlay_label(label: str) -> str:
    """Shorten ``label`` to what a small-icon overlay can hold.

    Args:
        label: The badge text.

    Returns:
        ``"99+"`` for a count above 99, otherwise the first three characters.
    """
    if label.isascii() and label.isdigit() and int(label) > _MAX_COUNT:
        return f"{_MAX_COUNT}+"
    return label[:_MAX_TEXT_LENGTH]


def render_overlay_bgra(label: str, size: int) -> bytes:
    """Draw ``label`` in white on a red disc filling a ``size`` x ``size`` icon.

    Args:
        label: The text, already shortened by :func:`overlay_label`.
        size: Edge length in pixels.

    Returns:
        Top-down BGRA rows with straight alpha.
    """
    skia = get_skia(raise_if_missing=True)

    surface = skia.Surface(size, size)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)

    fill = skia.Paint(AntiAlias=True, Color=_FILL)
    canvas.drawCircle(size / 2, size / 2, size / 2, fill)

    font = _fitted_font(skia, label, size)
    bounds = skia.Rect()
    font.measureText(label, skia.TextEncoding.kUTF8, bounds)
    # Centred on the ink, not the advance: digits sit off-centre in their advance box.
    x = (size - bounds.width()) / 2 - bounds.left()
    y = (size - bounds.height()) / 2 - bounds.top()
    canvas.drawString(label, x, y, font, skia.Paint(AntiAlias=True, Color=_TEXT))

    info = skia.ImageInfo.Make(size, size, skia.kBGRA_8888_ColorType, skia.kUnpremul_AlphaType)
    pixels = bytearray(size * size * 4)
    if not surface.makeImageSnapshot().readPixels(info, pixels, size * 4):
        raise RuntimeError("the badge overlay could not be read back")
    return bytes(pixels)


def _fitted_font(skia: Any, label: str, size: int) -> Any:
    """The largest bold font, up to the first size tried, that keeps ``label`` inside the disc."""
    typeface = skia.Typeface("", skia.FontStyle.Bold())
    font_size = size * _FONT_SHARE
    font = skia.Font(typeface, font_size)
    width = font.measureText(label)
    if width > size * _TEXT_SHARE:
        font = skia.Font(typeface, max(_MIN_FONT_SIZE, font_size * size * _TEXT_SHARE / width))
    return font
