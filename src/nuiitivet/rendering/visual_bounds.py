"""Paint outsets of a rect drawn under a canvas transform."""

from __future__ import annotations

import math
from typing import Optional, Tuple


def transformed_outsets(
    width: float,
    height: float,
    *,
    translate: Tuple[float, float] = (0.0, 0.0),
    scale: Tuple[float, float] = (1.0, 1.0),
    rotation: float = 0.0,
    origin: Optional[Tuple[float, float]] = None,
) -> Tuple[int, int, int, int]:
    """Return how far a ``width`` x ``height`` rect paints outside itself once transformed.

    The transform is the one canvases compose for a widget: scale and rotate
    about ``origin`` (the rect's centre when omitted), then translate. The
    result is the bounding box of the transformed corners, expressed as
    ``(left, top, right, bottom)`` outsets from the untransformed rect,
    rounded outwards and never negative.

    Args:
        width: Rect width in pixels.
        height: Rect height in pixels.
        translate: ``(dx, dy)`` applied after scaling and rotating.
        scale: ``(sx, sy)`` about ``origin``.
        rotation: Degrees clockwise about ``origin``.
        origin: Point the rect scales and rotates about, relative to the rect.
    """

    ox, oy = origin if origin is not None else (width / 2.0, height / 2.0)
    sx, sy = scale
    dx, dy = translate
    cos = math.cos(math.radians(rotation))
    sin = math.sin(math.radians(rotation))

    xs = []
    ys = []
    for px, py in ((0.0, 0.0), (width, 0.0), (0.0, height), (width, height)):
        lx = (px - ox) * sx
        ly = (py - oy) * sy
        xs.append(lx * cos - ly * sin + ox + dx)
        ys.append(lx * sin + ly * cos + oy + dy)

    return (
        int(math.ceil(max(0.0, -min(xs)))),
        int(math.ceil(max(0.0, -min(ys)))),
        int(math.ceil(max(0.0, max(xs) - width))),
        int(math.ceil(max(0.0, max(ys) - height))),
    )
