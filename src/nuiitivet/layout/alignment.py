from __future__ import annotations

import warnings
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

# Single-axis tokens accepted as shorthand (applied to both axes), e.g. "start".
_AXIS_VALUES: frozenset[str] = frozenset({"start", "center", "end"})


def normalize_alignment(value: AlignmentLike, *, default: Tuple[str, str]) -> Tuple[str, str]:
    """Normalize an alignment value to an ``(horizontal, vertical)`` axis tuple.

    The canonical string form is the hyphenated nine-point vocabulary
    (``top-left``, ``bottom-center``, ...). The underscore form (``top_left``)
    is accepted as an alias. A single-axis token (``start``/``center``/``end``)
    is accepted as shorthand applied to both axes. Unrecognized strings emit a
    :class:`UserWarning` and fall back to ``(value, value)``.
    """
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (str(value[0]), str(value[1]))

    if isinstance(value, str):
        key = value.strip().lower().replace("_", "-")
        if key in _NINE_POINT_ALIASES:
            return _NINE_POINT_ALIASES[key]
        if key not in _AXIS_VALUES:
            warnings.warn(
                f"Unrecognized alignment value {value!r}; expected one of "
                f"{sorted(NINE_POINT_ALIGNMENTS)} or {sorted(_AXIS_VALUES)}. "
                f"Falling back to {(value, value)!r}.",
                stacklevel=2,
            )
        return (value, value)

    return default


def alignment_to_point(alignment: Tuple[str, str], width: int, height: int) -> Tuple[float, float]:
    """Compute the ``(x, y)`` point for *alignment* within a box of the given size.

    *alignment* is an ``(horizontal, vertical)`` axis tuple as returned by
    :func:`normalize_alignment`.
    """
    ax, ay = alignment
    px = float(width) / 2.0 if ax == "center" else (float(width) if ax == "end" else 0.0)
    py = float(height) / 2.0 if ay == "center" else (float(height) if ay == "end" else 0.0)
    return (px, py)
