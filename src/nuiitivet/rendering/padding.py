"""Padding utilities."""

from __future__ import annotations

from typing import Tuple, Union

PaddingLike = Union[int, Tuple[int, int], Tuple[int, int, int, int], None]


def parse_padding(pad: PaddingLike) -> Tuple[int, int, int, int]:
    """Normalize a padding value into a 4-tuple (left, top, right, bottom).

    Accepted inputs:
    - int -> uniform padding on all sides
    - (h, v) -> horizontal, vertical -> (h, v, h, v)
    - (l, t, r, b) -> returned as-is
    - None -> (0, 0, 0, 0)

    Raises:
        ValueError: if the input is invalid or contains negative values.
    """
    if pad is None:
        return (0, 0, 0, 0)

    if isinstance(pad, int):
        if pad < 0:
            raise ValueError("padding must be non-negative")
        return (pad, pad, pad, pad)

    if isinstance(pad, (list, tuple)):
        if len(pad) == 2:
            h, v = pad
            if h < 0 or v < 0:
                raise ValueError("padding values must be non-negative")
            return (int(h), int(v), int(h), int(v))
        if len(pad) == 4:
            l, t, r, b = pad
            if l < 0 or t < 0 or r < 0 or b < 0:
                raise ValueError("padding values must be non-negative")
            return (int(l), int(t), int(r), int(b))

    raise ValueError(f"unsupported padding value: {pad!r}")
