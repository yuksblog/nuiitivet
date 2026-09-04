"""Mask filter helpers for the Skia backend."""

from __future__ import annotations

import logging
from typing import Any, Optional

from nuiitivet.common.logging_once import debug_once, exception_once

from .skia_module import get_skia


logger = logging.getLogger(__name__)


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
    "make_blur_mask_filter",
    "set_paint_mask_filter",
]
