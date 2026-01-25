"""Sizing parsing helpers for widget layout.

A Sizing represents the strategy a widget uses to request space along an axis.
Developers can pass ints, "auto", or percentage strings (e.g. "50%"), which are
converted into one of the supported Sizing variants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Tuple, Union

SizingKind = Literal["fixed", "auto", "flex"]
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
    def flex(cls, weight: float = 1.0) -> "Sizing":
        if weight <= 0:
            return cls.auto()
        return cls("flex", float(weight))


_AUTO = Sizing.auto()
_SIZING_CACHE: Dict[Tuple[Any, ...], Sizing] = {}
_SIZING_CACHE_STATS = {"parse_hits": 0, "parse_misses": 0}
_SIZING_CACHE_PROFILE_ENABLED = False


def parse_sizing(value: SizingLike, *, default: Sizing | None = None) -> Sizing:
    """Normalize a user-provided width/height spec into a Sizing.

    Accepted inputs:
    - int/float -> Fixed(value)
    - "auto" (case-insensitive) -> Auto
    - "{f}%" -> Flex(f)
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
        if trimmed.endswith("%"):
            num = trimmed[:-1].strip()
            if not num:
                raise ValueError("percentage sizing missing numeric weight")
            weight = float(num)
            if weight <= 0:
                raise ValueError("percentage weight must be positive")
            return Sizing.flex(weight)
        raise ValueError(f"unsupported sizing string: {value!r}")

    raise TypeError(f"unsupported sizing type: {type(value).__name__}")
