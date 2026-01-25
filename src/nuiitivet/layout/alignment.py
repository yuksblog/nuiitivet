from __future__ import annotations

from typing import Tuple, Union


AlignmentLike = Union[str, Tuple[str, str], None]


_NINE_POINT_ALIASES: dict[str, Tuple[str, str]] = {
    "top-left": ("start", "start"),
    "top-center": ("center", "start"),
    "top-right": ("end", "start"),
    "center-left": ("start", "center"),
    "center": ("center", "center"),
    "center-right": ("end", "center"),
    "bottom-left": ("start", "end"),
    "bottom-center": ("center", "end"),
    "bottom-right": ("end", "end"),
}


NINE_POINT_ALIGNMENTS: frozenset[str] = frozenset(_NINE_POINT_ALIASES.keys())


def normalize_alignment(value: AlignmentLike, *, default: Tuple[str, str]) -> Tuple[str, str]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (str(value[0]), str(value[1]))

    if isinstance(value, str):
        key = value.strip().lower().replace("_", "-")
        if key in _NINE_POINT_ALIASES:
            return _NINE_POINT_ALIASES[key]
        return (value, value)

    return default
