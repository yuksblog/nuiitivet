"""Typeface loading helpers for the Skia backend."""

from __future__ import annotations

import functools
import os
import hashlib
import logging
import locale
import weakref
from typing import Optional, Tuple

from nuiitivet.common.logging_once import debug_once, exception_once

from .skia_module import get_skia


logger = logging.getLogger(__name__)

# Simple typeface cache to avoid repeated disk/API calls
_TYPEFACE_CACHE: dict = {}

# Caches for direct typeface loading APIs.
_TYPEFACE_DIRECT_CACHE: dict = {}

_TYPEFACE_ID_REGISTRY: "weakref.WeakValueDictionary[int, object]" = weakref.WeakValueDictionary()

# User defined default font family
_USER_DEFAULT_FONT_FAMILY: Optional[str] = None


def set_default_font_family(family_name: Optional[str]) -> None:
    """Set the system-wide default font family.

    This font will be prioritized over locale-based defaults.
    Pass None to reset to automatic locale detection.
    """
    global _USER_DEFAULT_FONT_FAMILY
    _USER_DEFAULT_FONT_FAMILY = family_name


def get_default_font_fallbacks() -> Tuple[str, ...]:
    """Get the default font fallback list based on the system locale."""
    try:
        lang, _ = locale.getdefaultlocale()
    except Exception:
        lang = None

    # Common CJK fonts
    cjk_fonts = (
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Meiryo",
        "Yu Gothic",
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "MS Gothic",
        "AppleGothic",
    )

    # Common Western fonts
    western_fonts = (
        "DejaVu Sans",
        "Arial",
        "Helvetica",
        "Liberation Sans",
        "Segoe UI",
        "Roboto",
        "San Francisco",
        ".AppleSystemUIFont",  # macOS system font
    )

    fallbacks: Tuple[str, ...]

    if lang and lang.startswith("ja"):
        # Prioritize Japanese fonts for Japanese locale
        fallbacks = cjk_fonts + western_fonts
    else:
        # Default: Western fonts first, then CJK as fallback (to avoid tofu)
        fallbacks = western_fonts + cjk_fonts

    if _USER_DEFAULT_FONT_FAMILY:
        # Prepend the user specified font
        return (_USER_DEFAULT_FONT_FAMILY,) + fallbacks

    return fallbacks


def _register_typeface(typeface: object) -> int:
    tf_id = id(typeface)
    try:
        _TYPEFACE_ID_REGISTRY[tf_id] = typeface
    except Exception:
        # Best-effort only.
        pass
    return tf_id


@functools.lru_cache(maxsize=65536)
def _measure_text_width_cached(typeface_id: int, size: float, text: str) -> float:
    typeface = _TYPEFACE_ID_REGISTRY.get(typeface_id)
    if typeface is None:
        return 0.0

    font = make_font(typeface, size)
    if font is None:
        return 0.0

    measure = getattr(font, "measureText", None)
    if callable(measure):
        try:
            return float(measure(text))
        except Exception:
            exception_once(logger, "skia_font_measuretext_exc", "skia.Font.measureText failed")
            return 0.0

    # Fallback: sum per-glyph advances.
    # Do not use TextBlob.bounds() here; it can be overly conservative and
    # is not equivalent to advance width on some bindings.
    text_to_glyphs = getattr(font, "textToGlyphs", None)
    get_widths = getattr(font, "getWidths", None)
    if callable(text_to_glyphs) and callable(get_widths):
        try:
            glyphs = text_to_glyphs(str(text))
            widths = get_widths(glyphs)
            return float(sum(float(w) for w in widths))
        except Exception:
            exception_once(logger, "skia_font_getwidths_exc", "skia.Font.getWidths failed")
            return 0.0

    get_widths_bounds = getattr(font, "getWidthsBounds", None)
    if callable(text_to_glyphs) and callable(get_widths_bounds):
        try:
            glyphs = text_to_glyphs(str(text))
            widths, _bounds = get_widths_bounds(glyphs)
            return float(sum(float(w) for w in widths))
        except Exception:
            exception_once(logger, "skia_font_getwidthsbounds_exc", "skia.Font.getWidthsBounds failed")
            return 0.0

    return 0.0


@functools.lru_cache(maxsize=65536)
def _measure_text_ink_bounds_cached(typeface_id: int, size: float, text: str) -> Tuple[float, float, float, float]:
    """Measure tight ink bounds as (left, top, right, bottom)."""

    typeface = _TYPEFACE_ID_REGISTRY.get(typeface_id)
    if typeface is None:
        return (0.0, 0.0, 0.0, 0.0)

    font = make_font(typeface, size)
    if font is None:
        return (0.0, 0.0, 0.0, 0.0)

    text_value = str(text)
    if not text_value:
        return (0.0, 0.0, 0.0, 0.0)

    text_to_glyphs = getattr(font, "textToGlyphs", None)
    get_widths_bounds = getattr(font, "getWidthsBounds", None)
    if callable(text_to_glyphs) and callable(get_widths_bounds):
        try:
            glyphs = text_to_glyphs(text_value)
            widths, bounds = get_widths_bounds(glyphs)

            x = 0.0
            have = False
            left = top = right = bottom = 0.0
            for w, b in zip(widths, bounds):
                left_i = float(getattr(b, "left")()) + x
                top_i = float(getattr(b, "top")())
                right_i = float(getattr(b, "right")()) + x
                bottom_i = float(getattr(b, "bottom")())
                if not have:
                    left, top, right, bottom = left_i, top_i, right_i, bottom_i
                    have = True
                else:
                    left = min(left, left_i)
                    top = min(top, top_i)
                    right = max(right, right_i)
                    bottom = max(bottom, bottom_i)
                x += float(w)

            if have:
                return (left, top, right, bottom)
        except Exception:
            exception_once(logger, "skia_font_ink_bounds_exc", "Failed to measure text ink bounds")

    # Last-resort fallback: return an advance-only box.
    adv_w = float(measure_text_width(typeface, size, text_value))
    return (0.0, 0.0, adv_w, float(size))


def measure_text_ink_bounds(typeface: Optional[object], size: float, text: str) -> Tuple[float, float, float, float]:
    """Measure tight ink bounds as (left, top, right, bottom) with an LRU cache."""

    if typeface is None:
        return (0.0, 0.0, 0.0, 0.0)

    tf_id = _register_typeface(typeface)
    size_key = round(float(size), 3)
    return _measure_text_ink_bounds_cached(tf_id, size_key, str(text))


def measure_text_width(typeface: Optional[object], size: float, text: str) -> float:
    """Measure advance width with a process-wide LRU cache."""

    if typeface is None:
        return 0.0

    tf_id = _register_typeface(typeface)
    # Avoid unbounded key growth due to float representation noise.
    size_key = round(float(size), 3)
    return _measure_text_width_cached(tf_id, size_key, str(text))


def get_typeface(
    candidate_files: Optional[Tuple[str, ...]] = None,
    family_candidates: Optional[Tuple[str, ...]] = None,
    pkg_font_dir: Optional[str] = None,
    fallback_to_default: bool = True,
):
    """Load a skia.Typeface from paths or family names (cached)."""
    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    key = (
        tuple(candidate_files) if candidate_files is not None else None,
        tuple(family_candidates) if family_candidates is not None else None,
        pkg_font_dir,
        bool(fallback_to_default),
    )
    if key in _TYPEFACE_CACHE:
        return _TYPEFACE_CACHE[key]

    typeface = None

    if candidate_files:
        for fp in candidate_files:
            path = fp
            if not os.path.isabs(path) and pkg_font_dir:
                path = os.path.join(pkg_font_dir, path)

            try:
                if path and isinstance(path, str) and os.path.isfile(path):
                    try:
                        typeface = skia.Typeface.MakeFromFile(path)
                    except Exception:
                        try:
                            data = skia.Data.MakeFromFileName(path)
                            if data is not None:
                                typeface = skia.Typeface.MakeFromData(data)
                        except Exception:
                            exception_once(
                                logger,
                                "get_typeface_makefromfile_fallback_exc",
                                "Failed to load typeface via MakeFromFile and fallback Data.MakeFromFileName",
                            )
                            typeface = None
                    if typeface is not None:
                        _TYPEFACE_CACHE[key] = typeface
                        return typeface
            except Exception:
                exception_once(
                    logger,
                    "get_typeface_candidate_file_exc",
                    "Unexpected error while scanning candidate font files",
                )
                continue

    try:
        font_mgr = skia.FontMgr.RefDefault()
    except Exception:
        exception_once(logger, "skia_fontmgr_refdefault_exc", "skia.FontMgr.RefDefault failed")
        font_mgr = None

    if font_mgr is not None and family_candidates:
        try:
            for family in family_candidates:
                try:
                    typeface = font_mgr.matchFamilyStyle(family, skia.FontStyle())
                except Exception:
                    try:
                        typeface = skia.Typeface.MakeFromName(family, skia.FontStyle())
                    except Exception:
                        exception_once(
                            logger,
                            "get_typeface_makefromname_fallback_exc",
                            "skia.Typeface.MakeFromName raised (family=%s)",
                            family,
                        )
                        typeface = None
                if typeface is not None:
                    _TYPEFACE_CACHE[key] = typeface
                    return typeface
        except Exception:
            exception_once(logger, "get_typeface_matchfamily_exc", "Unexpected error while matching family candidates")

    if family_candidates:
        for family in family_candidates:
            try:
                typeface = skia.Typeface.MakeFromName(family, skia.FontStyle())
                if typeface is not None:
                    _TYPEFACE_CACHE[key] = typeface
                    return typeface
            except Exception:
                exception_once(
                    logger,
                    "get_typeface_makefromname_exc",
                    "skia.Typeface.MakeFromName raised (family=%s)",
                    family,
                )
                continue

    if fallback_to_default:
        try:
            font_mgr = skia.FontMgr.RefDefault()
        except Exception:
            exception_once(
                logger,
                "skia_fontmgr_refdefault_fallback_exc",
                "skia.FontMgr.RefDefault failed (fallback_to_default)",
            )
            font_mgr = None

        if font_mgr is not None:
            fam_name = None
            try:
                if hasattr(font_mgr, "getFamilyCount"):
                    count = font_mgr.getFamilyCount()
                    if count and count > 0 and hasattr(font_mgr, "getFamilyName"):
                        fam_name = font_mgr.getFamilyName(0)
                elif hasattr(font_mgr, "countFamilies"):
                    count = font_mgr.countFamilies()
                    if count and count > 0 and hasattr(font_mgr, "getFamilyName"):
                        fam_name = font_mgr.getFamilyName(0)
            except Exception:
                exception_once(logger, "skia_fontmgr_getfamily_exc", "skia.FontMgr getFamilyCount/getFamilyName failed")
                fam_name = None

            if fam_name:
                try:
                    typeface = font_mgr.matchFamilyStyle(fam_name, skia.FontStyle())
                    if typeface is not None:
                        _TYPEFACE_CACHE[key] = typeface
                        return typeface
                except Exception:
                    exception_once(logger, "skia_fontmgr_matchfamilystyle_exc", "skia.FontMgr.matchFamilyStyle failed")

    _TYPEFACE_CACHE[key] = None
    return None


def _cache_key_for_file(path: str) -> tuple[str, str]:
    return ("file", os.path.abspath(path))


def _cache_key_for_bytes(data: bytes) -> tuple[str, str, int]:
    digest = hashlib.sha256(data).hexdigest()
    return ("bytes", digest, len(data))


def _data_from_bytes(data: bytes):
    skia = get_skia(raise_if_missing=True)

    data_cls = getattr(skia, "Data", None)
    if data_cls is None:
        debug_once(logger, "skia_data_missing", "skia.Data is missing")
        return None

    maker = getattr(data_cls, "MakeFromBytes", None)
    if callable(maker):
        try:
            return maker(data)
        except Exception:
            exception_once(logger, "skia_data_makefrombytes_exc", "skia.Data.MakeFromBytes failed")

    debug_once(
        logger,
        "skia_data_makefrombytes_fallback",
        "skia.Data.MakeFromBytes unavailable; falling back to MakeWithCopy",
    )
    maker_copy = getattr(data_cls, "MakeWithCopy", None)
    if callable(maker_copy):
        try:
            return maker_copy(data)
        except Exception:
            exception_once(logger, "skia_data_makewithcopy_exc", "skia.Data.MakeWithCopy failed")
            return None

    debug_once(logger, "skia_data_makewithcopy_missing", "skia.Data.MakeWithCopy is missing")
    return None


def typeface_from_bytes(data: bytes) -> Optional[object]:
    """Create a typeface from raw font bytes.

    - Returns None on load failure.
    - Raises RuntimeError when skia is not installed (fail fast).
    """

    key = _cache_key_for_bytes(data)
    if key in _TYPEFACE_DIRECT_CACHE:
        return _TYPEFACE_DIRECT_CACHE[key]

    try:
        skia = get_skia(raise_if_missing=True)
        tf_cls = getattr(skia, "Typeface", None)
        if tf_cls is None:
            debug_once(logger, "skia_typeface_missing", "skia.Typeface is missing")
            _TYPEFACE_DIRECT_CACHE[key] = None
            return None

        data_obj = _data_from_bytes(data)
        if data_obj is None:
            _TYPEFACE_DIRECT_CACHE[key] = None
            return None

        maker = getattr(tf_cls, "MakeFromData", None)
        if callable(maker):
            try:
                tf = maker(data_obj)
                _TYPEFACE_DIRECT_CACHE[key] = tf
                return tf
            except Exception:
                exception_once(logger, "skia_typeface_makefromdata_exc", "skia.Typeface.MakeFromData failed")
                _TYPEFACE_DIRECT_CACHE[key] = None
                return None

        debug_once(logger, "skia_typeface_makefromdata_missing", "skia.Typeface.MakeFromData is missing")
        _TYPEFACE_DIRECT_CACHE[key] = None
        return None
    except RuntimeError:
        raise
    except Exception:
        exception_once(logger, "typeface_from_bytes_exc", "Unexpected error in typeface_from_bytes")
        _TYPEFACE_DIRECT_CACHE[key] = None
        return None


def typeface_from_file(path: str) -> Optional[object]:
    """Create a typeface from a font file.

    - Returns None on load failure.
    - Raises RuntimeError when skia is not installed (fail fast).
    """

    key = _cache_key_for_file(path)
    if key in _TYPEFACE_DIRECT_CACHE:
        return _TYPEFACE_DIRECT_CACHE[key]

    try:
        skia = get_skia(raise_if_missing=True)
        tf_cls = getattr(skia, "Typeface", None)
        if tf_cls is None:
            debug_once(logger, "skia_typeface_missing", "skia.Typeface is missing")
            _TYPEFACE_DIRECT_CACHE[key] = None
            return None

        if not path or not isinstance(path, str) or not os.path.isfile(path):
            _TYPEFACE_DIRECT_CACHE[key] = None
            return None

        maker_file = getattr(tf_cls, "MakeFromFile", None)
        if callable(maker_file):
            try:
                tf = maker_file(path)
                _TYPEFACE_DIRECT_CACHE[key] = tf
                return tf
            except Exception:
                exception_once(logger, "skia_typeface_makefromfile_exc", "skia.Typeface.MakeFromFile failed")

        debug_once(
            logger,
            "skia_typeface_makefromfile_fallback",
            "skia.Typeface.MakeFromFile unavailable; falling back to Data.MakeFromFileName",
        )

        data_cls = getattr(skia, "Data", None)
        maker_data_file = getattr(data_cls, "MakeFromFileName", None) if data_cls is not None else None
        if callable(maker_data_file):
            try:
                data_obj = maker_data_file(path)
            except Exception:
                exception_once(logger, "skia_data_makefromfilename_exc", "skia.Data.MakeFromFileName failed")
                data_obj = None
            if data_obj is not None:
                maker_data = getattr(tf_cls, "MakeFromData", None)
                if callable(maker_data):
                    try:
                        tf = maker_data(data_obj)
                        _TYPEFACE_DIRECT_CACHE[key] = tf
                        return tf
                    except Exception:
                        exception_once(logger, "skia_typeface_makefromdata_exc", "skia.Typeface.MakeFromData failed")

        _TYPEFACE_DIRECT_CACHE[key] = None
        return None
    except RuntimeError:
        raise
    except Exception:
        exception_once(logger, "typeface_from_file_exc", "Unexpected error in typeface_from_file")
        _TYPEFACE_DIRECT_CACHE[key] = None
        return None


def make_font(typeface: Optional[object], size: float) -> Optional[object]:
    """Create a skia.Font.

    Returns None when skia is not installed.
    """

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    if typeface is None:
        try:
            font_mgr = skia.FontMgr.RefDefault()
            if font_mgr is not None:
                typeface = font_mgr.matchFamilyStyle(None, skia.FontStyle())
        except Exception:
            exception_once(logger, "skia_fontmgr_default_typeface_exc", "Failed to resolve default typeface")

    if typeface is None:
        typeface = get_typeface(
            family_candidates=("DejaVu Sans", "Arial", "Helvetica", "Liberation Sans"),
            fallback_to_default=False,
        )

    try:
        return skia.Font(typeface, float(size))
    except Exception:
        exception_once(logger, "skia_font_ctor_exc", "skia.Font(...) failed")
        return None


def make_text_blob(text: str, font) -> Optional[object]:
    """Create a skia.TextBlob from string and font.

    Returns None when skia is not installed.
    """

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    tb_cls = getattr(skia, "TextBlob", None)
    maker = getattr(tb_cls, "MakeFromString", None) if tb_cls is not None else None
    if not callable(maker):
        debug_once(logger, "skia_textblob_makefromstring_missing", "skia.TextBlob.MakeFromString is missing")
        return None
    try:
        return maker(str(text), font)
    except Exception:
        exception_once(logger, "skia_textblob_makefromstring_exc", "skia.TextBlob.MakeFromString failed")
        return None


def _clear_typeface_caches_for_tests() -> None:
    """Clear internal typeface caches (tests only)."""

    try:
        _TYPEFACE_CACHE.clear()
        _TYPEFACE_DIRECT_CACHE.clear()
    except Exception:
        exception_once(logger, "clear_typeface_caches_exc", "Failed to clear typeface caches")


__all__ = [
    "get_typeface",
    "get_default_font_fallbacks",
    "set_default_font_family",
    "typeface_from_bytes",
    "typeface_from_file",
    "make_font",
    "make_text_blob",
    "measure_text_width",
    "measure_text_ink_bounds",
]
