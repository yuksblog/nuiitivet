"""Image filter and mask filter helpers for the Skia backend."""

from __future__ import annotations

import logging
from typing import Any, Optional

from nuiitivet.common.logging_once import debug_once, exception_once

from .skia_module import get_skia


logger = logging.getLogger(__name__)


def get_tile_mode_clamp_or_decal() -> Optional[Any]:
    """Return a TileMode suitable for blur filters.

    Prefers kClamp; falls back to kDecal when clamp is unavailable.
    """

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    tile_mode = getattr(skia, "TileMode", None)
    if tile_mode is None:
        debug_once(logger, "skia_tilemode_missing", "skia.TileMode is missing")
        return None

    try:
        return tile_mode.kClamp
    except Exception:
        try:
            return tile_mode.kDecal
        except Exception:
            debug_once(logger, "skia_tilemode_no_clamp", "TileMode.kClamp/kDecal unavailable")
            return None


def make_blur_image_filter(sigma: float) -> Optional[Any]:
    """Create a blur ImageFilter or return None if unavailable."""

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    image_filters = getattr(skia, "ImageFilters", None)
    if image_filters is None:
        debug_once(logger, "skia_imagefilters_missing", "skia.ImageFilters is missing")
        return None

    blur = getattr(image_filters, "Blur", None)
    if not callable(blur):
        debug_once(logger, "skia_blur_missing", "skia.ImageFilters.Blur is missing")
        return None

    try:
        tile = get_tile_mode_clamp_or_decal()
        if tile is not None:
            return blur(float(sigma), float(sigma), tile)
        return blur(float(sigma), float(sigma))
    except Exception:
        exception_once(logger, "skia_blur_exc", "ImageFilters.Blur failed")
        return None


def make_blur_mask_filter(sigma: float) -> Optional[Any]:
    """Create a blur MaskFilter or return None if unavailable."""

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    mask_filter = getattr(skia, "MaskFilter", None)
    if mask_filter is None:
        debug_once(logger, "skia_maskfilter_missing", "skia.MaskFilter is missing")
        return None

    maker = getattr(mask_filter, "MakeBlur", None)
    if not callable(maker):
        debug_once(logger, "skia_maskfilter_makeblur_missing", "MaskFilter.MakeBlur is missing")
        return None

    try:
        blur_style = getattr(skia, "kNormal_BlurStyle", None)
        if blur_style is None:
            blur_style = getattr(skia, "kNormal", 0)
        return maker(blur_style, float(sigma))
    except Exception:
        exception_once(logger, "skia_maskfilter_makeblur_exc", "MaskFilter.MakeBlur failed")
        return None


def set_paint_image_filter(paint: Any, image_filter: Any) -> bool:
    """Set ImageFilter to paint. Returns True when applied."""

    if paint is None or image_filter is None:
        return False

    setter = getattr(paint, "setImageFilter", None)
    if not callable(setter):
        debug_once(logger, "paint_setimagefilter_missing", "paint.setImageFilter is missing")
        return False

    try:
        setter(image_filter)
        return True
    except Exception:
        exception_once(logger, "paint_setimagefilter_exc", "paint.setImageFilter failed")
        return False


def set_paint_mask_filter(paint: Any, mask_filter: Any) -> bool:
    """Set MaskFilter to paint. Returns True when applied."""

    if paint is None or mask_filter is None:
        return False

    setter = getattr(paint, "setMaskFilter", None)
    if not callable(setter):
        debug_once(logger, "paint_setmaskfilter_missing", "paint.setMaskFilter is missing")
        return False

    try:
        setter(mask_filter)
        return True
    except Exception:
        exception_once(logger, "paint_setmaskfilter_exc", "paint.setMaskFilter failed")
        return False


__all__ = [
    "get_tile_mode_clamp_or_decal",
    "make_blur_image_filter",
    "make_blur_mask_filter",
    "set_paint_image_filter",
    "set_paint_mask_filter",
]
