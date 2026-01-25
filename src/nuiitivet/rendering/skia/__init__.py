"""Skia backend helpers for nuiitivet rendering."""

from __future__ import annotations

from typing import Any

from .skia_module import get_skia
from .color import (
    make_paint,
    make_opacity_paint,
    skcolor,
    rgba_to_skia_color,
)
from .font import (
    get_typeface,
    make_font,
    make_text_blob,
    measure_text_ink_bounds,
    measure_text_width,
    typeface_from_bytes,
    typeface_from_file,
    get_default_font_fallbacks,
)
from .geometry import (
    make_rect,
    make_rrect,
    resolve_rrect,
    draw_round_rect,
    clip_round_rect,
    clip_rect,
    make_point,
    draw_oval,
    make_path,
    path_add_rect,
    path_add_rrect,
    path_move_to,
    path_line_to,
)

from .surface import (
    make_raster_surface,
    save_png,
)

from .effects import (
    make_blur_image_filter,
    make_blur_mask_filter,
    set_paint_image_filter,
    set_paint_mask_filter,
)


def require_skia() -> Any:
    return get_skia(raise_if_missing=True)


__all__ = [
    "get_skia",
    "require_skia",
    "make_paint",
    "make_opacity_paint",
    "skcolor",
    "rgba_to_skia_color",
    "get_typeface",
    "typeface_from_bytes",
    "typeface_from_file",
    "get_default_font_fallbacks",
    "make_font",
    "make_text_blob",
    "measure_text_ink_bounds",
    "measure_text_width",
    "make_rect",
    "make_rrect",
    "resolve_rrect",
    "draw_round_rect",
    "clip_round_rect",
    "clip_rect",
    "make_point",
    "draw_oval",
    "make_path",
    "path_add_rect",
    "path_add_rrect",
    "path_move_to",
    "path_line_to",
    "make_raster_surface",
    "save_png",
    "make_blur_image_filter",
    "make_blur_mask_filter",
    "set_paint_image_filter",
    "set_paint_mask_filter",
]
