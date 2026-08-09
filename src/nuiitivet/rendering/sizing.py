"""Sizing parsing helpers for widget layout.

A Sizing represents the strategy a widget uses to request space along an axis.
Developers can pass ints, "auto", or weight strings (e.g. "wt", "wt2"), which
are converted into one of the supported Sizing variants.

A weight is a share of the *leftover* space, in the spirit of WPF star sizing:
"fixed" and "auto" children take what they ask for, and what remains on the
axis is split among the "weight" children in proportion to their weights. A
lone weight child therefore fills the axis whatever its weight.
See docs/design/SIZE_POLICY.md 1.1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Literal, Tuple, Union

SizingKind = Literal["fixed", "auto", "weight"]
SizingLike = Union["Sizing", int, float, str, None]


@dataclass(frozen=True)
class Sizing:
    kind: SizingKind
    value: float = 0.0

    @classmethod
    def fixed(cls, value: float) -> "Sizing":
        return cls("fixed", float(value))

    @classmethod
    def auto(cls) -> "Sizing":
        return cls("auto", 0.0)

    @classmethod
    def weight(cls, value: float = 1.0) -> "Sizing":
        if value <= 0:
            return cls.auto()
        return cls("weight", float(value))


_AUTO = Sizing.auto()
_WEIGHT_ONE = Sizing.weight(1.0)
_SIZING_CACHE: Dict[Tuple[Any, ...], Sizing] = {}
_SIZING_CACHE_STATS = {"parse_hits": 0, "parse_misses": 0}
_SIZING_CACHE_PROFILE_ENABLED = False


def parse_sizing(value: SizingLike, *, default: Sizing | None = None) -> Sizing:
    """Normalize a user-provided width/height spec into a Sizing.

    Accepted inputs (strings are case-insensitive):
    - int/float -> Sizing.fixed(value)
    - "auto" -> Sizing.auto()
    - "wt" -> Sizing.weight(1)
    - "wt{f}" -> Sizing.weight(f), e.g. "wt2", "wt0.5"
    - Sizing -> returned as-is
    - None -> `default` if provided, else Auto
    """

    if isinstance(value, Sizing):
        return value

    key = _sizing_cache_key(value, default)
    cached = _SIZING_CACHE.get(key)
    if cached is not None:
        _record_sizing_cache_event("parse_hits")
        return cached

    result = _parse_sizing_value(value, default=default)
    _SIZING_CACHE[key] = result
    _record_sizing_cache_event("parse_misses")
    return result


__all__ = [
    "Sizing",
    "SizingKind",
    "SizingLike",
    "parse_sizing",
    "sizing_signature",
    "enable_sizing_cache_profiling",
    "reset_sizing_cache_stats",
    "get_sizing_cache_stats",
    "clear_sizing_cache",
]


def sizing_signature(value: SizingLike) -> Tuple[str, float]:
    """Return a stable tuple usable as a cache key for a sizing."""

    dim = value if isinstance(value, Sizing) else parse_sizing(value)
    return (dim.kind, float(dim.value))


def enable_sizing_cache_profiling(enabled: bool) -> None:
    global _SIZING_CACHE_PROFILE_ENABLED
    _SIZING_CACHE_PROFILE_ENABLED = bool(enabled)


def reset_sizing_cache_stats() -> None:
    for key in _SIZING_CACHE_STATS:
        _SIZING_CACHE_STATS[key] = 0


def get_sizing_cache_stats() -> Dict[str, int]:
    return dict(_SIZING_CACHE_STATS)


def clear_sizing_cache() -> None:
    _SIZING_CACHE.clear()


def _record_sizing_cache_event(event: str) -> None:
    if _SIZING_CACHE_PROFILE_ENABLED and event in _SIZING_CACHE_STATS:
        _SIZING_CACHE_STATS[event] += 1


def _sizing_cache_key(value: SizingLike, default: Sizing | None) -> Tuple[Any, ...]:
    if value is None:
        if default is None:
            return ("none",)
        return ("default", default.kind, float(default.value))
    if isinstance(value, (int, float)):
        return ("number", float(value))
    if isinstance(value, str):
        return ("str", value.strip().lower())
    if isinstance(value, Sizing):  # pragma: no cover - handled earlier
        return ("dim", value.kind, float(value.value))
    raise TypeError(f"unsupported sizing type: {type(value).__name__}")


def _parse_sizing_value(value: SizingLike, *, default: Sizing | None) -> Sizing:
    if value is None:
        return default if default is not None else _AUTO

    if isinstance(value, (int, float)):
        if value < 0:
            raise ValueError("sizing value must be non-negative")
        return Sizing.fixed(value)

    if isinstance(value, str):
        trimmed = value.strip().lower()
        if trimmed == "auto":
            return _AUTO
        if trimmed.startswith("wt"):
            num = trimmed[2:].strip()
            if not num:
                return _WEIGHT_ONE
            try:
                weight = float(num)
            except ValueError:
                raise ValueError(f"unsupported sizing string: {value!r}") from None
            if not math.isfinite(weight) or weight <= 0:
                raise ValueError("weight must be a positive finite number")
            return Sizing.weight(weight)
        raise ValueError(f"unsupported sizing string: {value!r}")

    raise TypeError(f"unsupported sizing type: {type(value).__name__}")
