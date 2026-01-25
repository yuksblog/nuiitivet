"""Pure color utilities used by theme and rendering.

These functions are intentionally independent from `theme` and
`rendering` modules so they are safe to import from either side.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union
from functools import lru_cache

from nuiitivet.common.logging_once import exception_once

from .names import CSS_COLORS


logger = logging.getLogger(__name__)


def _normalize_hex(s: str) -> str:
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
    return s


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert a hex color string like "#RRGGBB" to an (r, g, b) tuple.

    Accepts short form like #RGB as well.
    """
    s = _normalize_hex(hex_str)
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"Invalid hex color: {hex_str}")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r, g, b)


def _srgb_to_linear(c: float) -> float:
    """Convert an sRGB component in [0,1] to linear value per WCAG."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_str: str) -> float:
    """Compute relative luminance for a hex color per WCAG definition.

    Returns a value in [0, 1].
    """
    r, g, b = hex_to_rgb(hex_str)
    rs = r / 255.0
    gs = g / 255.0
    bs = b / 255.0
    lr = _srgb_to_linear(rs)
    lg = _srgb_to_linear(gs)
    lb = _srgb_to_linear(bs)
    # Rec. 709 luminance coefficients
    return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb


def contrast_ratio(foreground_hex: str, background_hex: str) -> float:
    """Return the contrast ratio (>=1.0) between two hex colors.

    Formula: (L1 + 0.05) / (L2 + 0.05) where L1 >= L2 are relative luminances.
    """
    l1 = relative_luminance(foreground_hex)
    l2 = relative_luminance(background_hex)
    hi = max(l1, l2)
    lo = min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def passes_wcag(foreground_hex: str, background_hex: str, *, level: str = "AA", large: bool = False) -> bool:
    """Return True if the color pair meets WCAG contrast requirements.

    level: "AA" or "AAA". large: if True uses large text thresholds.
    """
    ratio = contrast_ratio(foreground_hex, background_hex)
    if level == "AA":
        return ratio >= (3.0 if large else 4.5)
    if level == "AAA":
        return ratio >= (4.5 if large else 7.0)
    raise ValueError("level must be 'AA' or 'AAA'")


def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB (0-255) to HSL (h in degrees 0..360, s and l in 0..1)."""
    r_, g_, b_ = float(r) / 255.0, float(g) / 255.0, float(b) / 255.0
    mx = max(r_, g_, b_)
    mn = min(r_, g_, b_)
    d = mx - mn
    lightness = (mx + mn) / 2
    if d == 0:
        return 0.0, 0.0, lightness
    s = d / (1 - abs(2 * lightness - 1))
    if mx == r_:
        h = ((g_ - b_) / d) % 6
    elif mx == g_:
        h = (b_ - r_) / d + 2
    else:
        h = (r_ - g_) / d + 4
    h = h * 60
    return h, s, lightness


def hsl_to_rgb(h: float, s: float, lightness: float) -> Tuple[int, int, int]:
    """Convert HSL values to RGB tuple of ints (0-255)."""
    c = (1 - abs(2 * lightness - 1)) * s
    hh = h / 60.0
    x = c * (1 - abs(hh % 2 - 1))
    m = lightness - c / 2
    r1: float = 0.0
    g1: float = 0.0
    b1: float = 0.0
    if 0 <= hh < 1:
        r1, g1, b1 = c, x, 0.0
    elif 1 <= hh < 2:
        r1, g1, b1 = x, c, 0.0
    elif 2 <= hh < 3:
        r1, g1, b1 = 0.0, c, x
    elif 3 <= hh < 4:
        r1, g1, b1 = 0.0, x, c
    elif 4 <= hh < 5:
        r1, g1, b1 = x, 0.0, c
    else:
        r1, g1, b1 = c, 0.0, x
    val_r: int = int(round((r1 + m) * 255))
    val_g: int = int(round((g1 + m) * 255))
    val_b: int = int(round((b1 + m) * 255))
    if val_r < 0:
        r_val = 0
    elif val_r > 255:
        r_val = 255
    else:
        r_val = val_r

    if val_g < 0:
        g_val = 0
    elif val_g > 255:
        g_val = 255
    else:
        g_val = val_g

    if val_b < 0:
        b_val = 0
    elif val_b > 255:
        b_val = 255
    else:
        b_val = val_b
    return r_val, g_val, b_val


def make_tone(h: float, s: float, lightness: float, sat_mult: float = 1.0) -> str:
    """Produce a hex color string from HSL tone parameters.

    sat_mult allows reducing saturation for container tones.
    """
    s2 = max(0.0, min(1.0, s * sat_mult))
    r, g, b = hsl_to_rgb(h, s2, lightness)
    return "#{:02X}{:02X}{:02X}".format(int(r), int(g), int(b))


def int_to_hex_rgb(argb: int) -> str:
    """Convert ARGB/RGB int to hex "#RRGGBB"; fall back to gray on error.

    Accepts either 0xAARRGGBB or 0xRRGGBB integer formats. Alpha is ignored.
    """
    try:
        r = (argb >> 16) & 0xFF
        g = (argb >> 8) & 0xFF
        b = argb & 0xFF
        return "#{:02X}{:02X}{:02X}".format(r, g, b)
    except Exception:
        exception_once(logger, "colors_int_to_hex_rgb_exc", "int_to_hex_rgb failed")
        return "#808080"


def pick_accessible_foreground(fg_hex: str, bg_hex: str, *, level: str = "AA", large: bool = False) -> str:
    """Return an accessible foreground color for `bg_hex`.

    If the provided `fg_hex` already meets the WCAG `level` threshold
    against `bg_hex`, it is returned unchanged. Otherwise choose between
    black (`#000000`) and white (`#FFFFFF`) whichever has higher contrast
    against `bg_hex`.
    """
    try:
        if passes_wcag(fg_hex, bg_hex, level=level, large=large):
            return fg_hex
        black = "#000000"
        white = "#FFFFFF"
        b_con = contrast_ratio(black, bg_hex)
        w_con = contrast_ratio(white, bg_hex)
        return black if b_con >= w_con else white
    except Exception:
        exception_once(logger, "colors_pick_accessible_foreground_exc", "pick_accessible_foreground failed")
        return fg_hex


def hex_to_rgba(hexstr: str, alpha: float = 1.0) -> Tuple[int, int, int, int]:
    """Convert hex color string to (r,g,b,a) tuple with 0-255 ints.

    Supports formats: "#rrggbb", "#rrggbbaa", "rrggbb", "rrggbbaa".
    The `alpha` parameter multiplies any alpha component found in the
    hex string (or sets alpha if none present).
    """
    s = hexstr.strip()
    if s.startswith("#"):
        s = s[1:]
    a = max(0.0, min(1.0, float(alpha)))
    try:
        r, g, b, base_a = _parse_hex_to_rgba_base(s)
        cand = int(a * float(base_a))
        a_val = int(max(0, min(255, cand)))
        return (r, g, b, a_val)
    except Exception:
        exception_once(logger, "colors_hex_to_rgba_exc", "hex_to_rgba failed")
        return (0, 0, 0, int(max(0, min(255, int(a * 255.0)))))


@lru_cache(maxsize=4096)
def _parse_hex_to_rgba_base(s: str) -> Tuple[int, int, int, int]:
    """Parse a hex color string into (r,g,b,a) without extra alpha multiplier."""

    # Normalize for cache hit rate.
    v = (s or "").strip()
    if v.startswith("#"):
        v = v[1:]
    v = v.strip()

    if len(v) in (3, 4):
        r = int(v[0] * 2, 16)
        g = int(v[1] * 2, 16)
        b = int(v[2] * 2, 16)
        if len(v) == 4:
            a_hex = int(v[3] * 2, 16)
            return (r, g, b, int(max(0, min(255, a_hex))))
        return (r, g, b, 255)

    if len(v) in (6, 8):
        r = int(v[0:2], 16)
        g = int(v[2:4], 16)
        b = int(v[4:6], 16)
        if len(v) == 8:
            a_hex = int(v[6:8], 16)
            return (r, g, b, int(max(0, min(255, a_hex))))
        return (r, g, b, 255)

    # Fallback: try parsing first 6 chars if available.
    if len(v) >= 6:
        r = int(v[0:2], 16)
        g = int(v[2:4], 16)
        b = int(v[4:6], 16)
        return (r, g, b, 255)

    return (0, 0, 0, 255)


def apply_alpha_to_rgba(rgba: Tuple[int, int, int, int], alpha: float) -> Tuple[int, int, int, int]:
    """Apply an extra alpha multiplier to an existing RGBA tuple.

    `alpha` is between 0.0 and 1.0. Returns a new RGBA tuple.
    """
    r, g, b, a = rgba
    a = int(round(a * float(alpha)))
    return (int(r), int(g), int(b), int(a))


def normalize_literal_color(val: object) -> Optional[Union[str, Tuple[int, int, int, int]]]:
    """Normalize literal color-like inputs.

    Accepts and normalizes these inputs:
    - hex string: returned as-is (str). Supports "#RGB", "#RRGGBB", with/without
      leading '#'.
    - int: treated as ARGB or RGB integer and converted to "#RRGGBB" (alpha ignored).
    - 3-tuple/list: treated as (r,g,b) and converted to "#RRGGBB" (values clamped).
    - 4-tuple/list: treated as RGBA/ARGB and returned as a 4-tuple of ints in the
      original order.
    - (str, float): treated as (hex_string, alpha) and converted via `hex_to_rgba`
      to an RGBA 4-tuple.

    Returns:
    - `str` hex for hex/int/3-tuple inputs.
    - `Tuple[int,int,int,int]` for 4-tuples or (hex, alpha) inputs.
    - `None` for unrecognized or malformed inputs.
    """

    # hex string
    if isinstance(val, str):
        if val.lower() in CSS_COLORS:
            return CSS_COLORS[val.lower()]
        return val

    # integer ARGB/RGB -> hex
    if isinstance(val, int):
        try:
            return int_to_hex_rgb(val)
        except Exception:
            exception_once(logger, "colors_normalize_int_exc", "normalize_literal_color int path failed")
            return None

    # sequences
    if isinstance(val, (list, tuple)):
        # 4-tuple RGBA -> return RGBA tuple
        if len(val) == 4:
            try:
                r, g, b, a = val
                return (int(r), int(g), int(b), int(a))
            except Exception:
                exception_once(logger, "colors_normalize_rgba_exc", "normalize_literal_color RGBA path failed")
                return None

        # 3-tuple RGB -> return hex string
        if len(val) == 3:
            try:
                r, g, b = (int(val[0]), int(val[1]), int(val[2]))
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return "#{:02X}{:02X}{:02X}".format(r, g, b)
            except Exception:
                exception_once(logger, "colors_normalize_rgb_exc", "normalize_literal_color RGB path failed")
                return None

        # (str, float) pair -> hex_to_rgba
        if len(val) == 2 and isinstance(val[0], str):
            try:
                hexstr, alpha = val[0], float(val[1])
                return hex_to_rgba(hexstr, alpha)
            except Exception:
                exception_once(logger, "colors_normalize_pair_exc", "normalize_literal_color (hex, alpha) path failed")
                return None

    return None


__all__ = [
    "hex_to_rgba",
    "hex_to_rgb",
    "apply_alpha_to_rgba",
    "normalize_literal_color",
    "relative_luminance",
    "contrast_ratio",
    "passes_wcag",
    "rgb_to_hsl",
    "hsl_to_rgb",
    "make_tone",
    "int_to_hex_rgb",
    "pick_accessible_foreground",
]
