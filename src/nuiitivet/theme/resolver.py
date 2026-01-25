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
from nuiitivet.theme.types import ColorSpec, ColorToken
from nuiitivet.theme.theme import Theme


logger = logging.getLogger(__name__)


def _default_role_resolver() -> Callable[[Any], Optional[str]]:
    def resolver(_: Any) -> Optional[str]:
        return None

    return resolver


def _to_rgba_from_normalized(lit: object, alpha: float = 1.0) -> Optional[Tuple[int, int, int, int]]:
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


def _apply_alpha_multiplier(rgba: Tuple[int, int, int, int], alpha: float) -> Tuple[int, int, int, int]:
    a_mult = _clamp01(float(alpha))
    r, g, b, a = rgba
    # Match `hex_to_rgba` behavior (truncate, not round).
    a_out = int(int(a) * a_mult)
    return (int(r), int(g), int(b), int(max(0, min(255, a_out))))


def resolve_color_to_rgba(
    val: Union[ColorSpec, Any],
    default: Optional[Union[ColorSpec, Any]] = None,
    role_resolver: Optional[Callable[[Any], Optional[str]]] = None,
    theme: Theme | None = None,
) -> Tuple[int, int, int, int]:
    """Resolve a ColorLike into an (r,g,b,a) tuple of ints (0-255).

    Rules:
    - If `val` is a literal (hex string or RGBA tuple) it's normalized.
        - If `val` is a pair (base, alpha) the base is resolved and alpha is applied
            as a multiplier to any resolved alpha (alpha is 0.0..1.0).
    - If `val` appears to be a ColorRole, `role_resolver` is used to get
      a hex string, which is then converted.
    - If `val` is None, `default` is attempted.
    - If resolution fails, returns transparent (0,0,0,0).
    """
    resolver = role_resolver if role_resolver is not None else _default_role_resolver()

    def _resolve_one(x: ColorSpec) -> Optional[Tuple[int, int, int, int]]:
        if x is None:
            return None

        # Handle (base, alpha) pairs early so the alpha semantics are consistent
        # across literal and token bases.
        if isinstance(x, (list, tuple)) and len(x) == 2:
            base = x[0]
            try:
                alpha = float(x[1])
            except Exception:
                alpha = None  # type: ignore[assignment]

            if alpha is not None:
                resolved_base_rgba: Optional[Tuple[int, int, int, int]] = None

                # token base
                if isinstance(base, ColorToken):
                    try:
                        resolved_base = base.resolve(theme)
                    except Exception:
                        exception_once(logger, "theme_resolver_token_resolve_base_exc", "ColorToken.resolve failed")
                        resolved_base = None
                    if resolved_base is not None:
                        resolved_base_rgba = _resolve_one(resolved_base)

                # literal base
                if resolved_base_rgba is None:
                    base_lit = normalize_literal_color(base)  # type: ignore[arg-type]
                    if base_lit is not None:
                        resolved_base_rgba = _to_rgba_from_normalized(base_lit, 1.0)

                # role base
                if resolved_base_rgba is None:
                    try:
                        hexv = resolver(base)
                    except Exception:
                        exception_once(
                            logger,
                            "theme_resolver_role_resolver_base_exc",
                            "role_resolver raised for base=%s",
                            type(base).__name__,
                        )
                        hexv = None
                    if hexv is not None:
                        resolved_base_rgba = _to_rgba_from_normalized(hexv, 1.0)

                if resolved_base_rgba is not None:
                    return _apply_alpha_multiplier(resolved_base_rgba, alpha)

        if isinstance(x, ColorToken):
            try:
                resolved = x.resolve(theme)
            except Exception:
                exception_once(logger, "theme_resolver_token_resolve_exc", "ColorToken.resolve failed")
                resolved = None
            if resolved is not None:
                return _resolve_one(resolved)

        # First, try to interpret as a literal value
        lit = normalize_literal_color(x)  # type: ignore[arg-type]
        if lit is not None:
            return _to_rgba_from_normalized(lit, 1.0)

        # try resolving as a role directly
        try:
            hexv = resolver(x)
        except Exception:
            exception_once(
                logger,
                "theme_resolver_role_resolver_exc",
                "role_resolver raised for value=%s",
                type(x).__name__,
            )
            hexv = None
        if hexv is not None:
            return _to_rgba_from_normalized(hexv, 1.0)

        return None

    res = _resolve_one(val)  # type: ignore[arg-type]
    if res is not None:
        return res

    # try default
    res = _resolve_one(default)  # type: ignore[arg-type]
    if res is not None:
        return res

    # fallback: transparent
    return (0, 0, 0, 0)


__all__ = ["resolve_color_to_rgba"]
