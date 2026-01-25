"""Color resolution and paint utilities for the Skia backend."""

from __future__ import annotations

import logging
from typing import Tuple

from nuiitivet.colors.utils import hex_to_rgba
from nuiitivet.common.logging_once import exception_once

from .skia_module import get_skia


_logger = logging.getLogger(__name__)


def skcolor(hexstr: str, alpha: float = 1.0):
    """Return a skia color when possible, otherwise an (r,g,b,a) tuple."""
    rgba = hex_to_rgba(hexstr, alpha)
    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return rgba
    try:
        return skia.ColorSetARGB(rgba[3], rgba[0], rgba[1], rgba[2])
    except Exception:
        exception_once(
            _logger,
            "skia_color_set_argb_exc",
            "skia.ColorSetARGB failed; falling back to RGBA tuple",
        )
        return rgba


def rgba_to_skia_color(rgba: Tuple[int, int, int, int]):
    """Convert an (r,g,b,a) tuple to a skia color object or return the tuple if skia missing."""
    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return rgba
    try:
        r, g, b, a = rgba
        return skia.ColorSetARGB(int(a), int(r), int(g), int(b))
    except Exception:
        exception_once(
            _logger,
            "rgba_to_skia_color_exc",
            "Failed to convert RGBA tuple to skia color; falling back to tuple",
        )
        return rgba


def make_paint(color=None, style: str = "fill", stroke_width: float = 1.0, aa: bool = True):
    """Create and return a configured skia.Paint (or None if unavailable)."""
    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    try:
        paint = skia.Paint()
        paint.setAntiAlias(bool(aa))

        style_const = getattr(skia.Paint, "kStroke_Style" if style == "stroke" else "kFill_Style", None)
        if style_const is not None:
            try:
                paint.setStyle(style_const)
            except Exception:
                exception_once(
                    _logger,
                    "skia_paint_set_style_exc",
                    "skia.Paint.setStyle failed",
                )

        try:
            paint.setStrokeWidth(float(stroke_width))
        except Exception:
            exception_once(
                _logger,
                "skia_paint_set_stroke_width_exc",
                "skia.Paint.setStrokeWidth failed",
            )

        if color is not None:
            try:
                # Accept primitive RGBA tuples directly.
                if isinstance(color, (list, tuple)) and len(color) == 4:
                    paint.setColor(rgba_to_skia_color(tuple(color)))
                # Accept integer color values (ARGB/ABGR ints) directly.
                elif isinstance(color, int):
                    paint.setColor(int(color))
                # Accept hex string for convenience.
                elif isinstance(color, str):
                    paint.setColor(skcolor(color))
                else:
                    # Unsupported high-level color types (ColorRole etc.)
                    # should be resolved at the theme layer. Ignore to avoid
                    # creating import cycles and to keep this backend strictly
                    # accepting primitive colors.
                    pass
            except Exception:
                exception_once(
                    _logger,
                    "skia_paint_set_color_exc",
                    "Failed to set paint color; ignoring",
                )

        return paint
    except Exception:
        exception_once(
            _logger,
            "skia_make_paint_exc",
            "Failed to create/configure skia.Paint",
        )
        return None


def make_opacity_paint(opacity: float):
    """Create a paint that applies uniform opacity to a saveLayer.

    This is used by widgets to apply a disabled-opacity layer without
    importing skia directly.
    """

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    try:
        paint = skia.Paint()
        # Prefer Color4f if available.
        color4f = getattr(skia, "Color4f", None)
        if callable(color4f):
            paint.setColor(color4f(1.0, 1.0, 1.0, float(opacity)))
        else:
            # Fallback: keep white and set alpha when possible.
            try:
                set_alphaf = getattr(paint, "setAlphaf", None)
                if callable(set_alphaf):
                    set_alphaf(float(opacity))
            except Exception:
                exception_once(
                    _logger,
                    "skia_paint_set_alphaf_exc",
                    "skia.Paint.setAlphaf failed",
                )
        return paint
    except Exception:
        exception_once(
            _logger,
            "skia_make_opacity_paint_exc",
            "Failed to create opacity paint",
        )
        return None


__all__ = [
    "skcolor",
    "make_paint",
    "rgba_to_skia_color",
    "make_opacity_paint",
]
