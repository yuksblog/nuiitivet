"""Resolve ColorLike / ColorRole into primitive RGBA values.

This module belongs to the theme layer — it knows how to convert
ColorRole values (via the theme manager) into concrete hex strings and
ultimately into RGBA tuples. It uses pure utilities from
`nuiitivet.colors.utils` and keeps any import of `nuiitivet.theme` lazy
so that rendering modules don't create import cycles.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once

from nuiitivet.colors.utils import (
    normalize_literal_color,
    hex_to_rgba,
    apply_alpha_to_rgba,
)
from nuiitivet.theme.types import ColorSpec
from nuiitivet.theme.theme import Theme

logger = logging.getLogger(__name__)


RGBA = Tuple[int, int, int, int]
RoleResolver = Callable[[Any], Optional[str]]


def _rgba_from_normalized(lit: object, alpha: float = 1.0) -> Optional[RGBA]:
    """Convert a normalized literal (hex string or tuple) to RGBA.

    `lit` is expected to be the output of `normalize_literal_color` (a
    hex `str` or a 4-tuple/3-tuple). `alpha` is applied as a multiplier to
    any returned alpha (for tuples) or passed to `hex_to_rgba` for hex
    strings. Returns None on failure.
    """
    if lit is None:
        return None

    # hex string
    if isinstance(lit, str):
        try:
            return hex_to_rgba(lit, alpha)
        except Exception:
            exception_once(logger, "theme_resolver_hex_to_rgba_exc", "hex_to_rgba failed in theme resolver")
            return None

    # tuple-like
    if isinstance(lit, (list, tuple)):
        try:
            if len(lit) == 4:
                # RGBA/ARGB (preserve order) -> apply extra alpha multiplier
                r, g, b, a = (int(lit[0]), int(lit[1]), int(lit[2]), int(lit[3]))
                return apply_alpha_to_rgba((r, g, b, a), alpha)
            if len(lit) >= 3:
                # treat as RGB-like (take last 3 values)
                vals = tuple(int(x) for x in lit[-3:])
                try:
                    return hex_to_rgba("#{:02X}{:02X}{:02X}".format(*vals), alpha)
                except Exception:
                    exception_once(logger, "theme_resolver_rgb_hex_to_rgba_exc", "hex_to_rgba failed in theme resolver")
                    return None
        except Exception:
            exception_once(logger, "theme_resolver_tuple_normalize_exc", "Failed to normalize tuple color")
            return None

    return None


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _apply_alpha_multiplier(rgba: RGBA, alpha: float) -> RGBA:
    a_mult = _clamp01(float(alpha))
    r, g, b, a = rgba
    # Match `hex_to_rgba` behavior (truncate, not round).
    a_out = int(int(a) * a_mult)
    return (int(r), int(g), int(b), int(max(0, min(255, a_out))))


def _resolve_token(token: Any, theme: Theme | None, role_resolver: Optional[RoleResolver]) -> Optional[RGBA]:
    """Resolve a :class:`ColorToken` through ``theme``; ``None`` if it has no value there."""
    try:
        resolved = token.resolve(theme)
    except Exception:
        exception_once(logger, "theme_resolver_token_resolve_exc", "ColorToken.resolve failed")
        return None
    if resolved is None:
        return None
    return _resolve_one(resolved, theme, role_resolver)


def _resolve_role(x: Any, role_resolver: RoleResolver) -> Optional[RGBA]:
    """Resolve ``x`` through the caller's ``role_resolver``; ``None`` if it declines."""
    try:
        hexv = role_resolver(x)
    except Exception:
        exception_once(
            logger,
            "theme_resolver_role_resolver_exc",
            "role_resolver raised for value=%s",
            type(x).__name__,
        )
        return None
    if hexv is None:
        return None
    return _rgba_from_normalized(hexv, 1.0)


def _resolve_one(x: Any, theme: Theme | None, role_resolver: Optional[RoleResolver]) -> Optional[RGBA]:
    # Literals first, and by concrete type: ``ColorToken`` is a runtime-checkable
    # Protocol, and on Python 3.10/3.11 an ``isinstance`` against one re-scans
    # the protocol's attributes on every call -- microseconds, on a path that
    # runs for every colour of every widget on every frame. Only what is left
    # after the literal checks is asked whether it can ``resolve``.
    if x is None:
        return None
    if isinstance(x, str):
        return _rgba_from_normalized(normalize_literal_color(x), 1.0)
    if isinstance(x, (list, tuple)):
        if len(x) == 2:
            # (base, alpha): the base resolves on its own, alpha multiplies
            # whatever alpha it resolved to, token and literal bases alike.
            base = x[0]
            try:
                alpha: Optional[float] = float(x[1])
            except Exception:
                alpha = None
            if alpha is not None:
                base_rgba = _resolve_one(base, theme, role_resolver)
                if base_rgba is not None:
                    return _apply_alpha_multiplier(base_rgba, alpha)
        return _rgba_from_normalized(normalize_literal_color(x), 1.0)
    if isinstance(x, int):
        return _rgba_from_normalized(normalize_literal_color(x), 1.0)
    if getattr(x, "resolve", None) is not None:
        rgba = _resolve_token(x, theme, role_resolver)
        if rgba is not None:
            return rgba
    if role_resolver is not None:
        return _resolve_role(x, role_resolver)
    return None


def resolve_color_to_rgba(
    val: Union[ColorSpec, Any],
    default: Optional[Union[ColorSpec, Any]] = None,
    role_resolver: Optional[RoleResolver] = None,
    theme: Theme | None = None,
) -> RGBA:
    """Resolve a ColorLike into an (r,g,b,a) tuple of ints (0-255).

    Rules:
    - If `val` is a literal (hex string or RGBA tuple) it's normalized.
        - If `val` is a pair (base, alpha) the base is resolved and alpha is applied
            as a multiplier to any resolved alpha (alpha is 0.0..1.0).
    - If `val` is a `ColorToken`, it is resolved through `theme`.
    - Otherwise `role_resolver`, when given, may turn `val` into a hex string.
    - If `val` is None, `default` is attempted.
    - If resolution fails, returns transparent (0,0,0,0).
    """
    res = _resolve_one(val, theme, role_resolver)
    if res is not None:
        return res

    # try default
    res = _resolve_one(default, theme, role_resolver)
    if res is not None:
        return res

    # fallback: transparent
    return (0, 0, 0, 0)


__all__ = ["resolve_color_to_rgba"]
