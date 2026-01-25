"""Expressive shape helpers.

This module provides lightweight, drawable shape approximations for M3 Expressive
components.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import copysign, cos, pi, sin
from typing import Dict, Iterable, List, Sequence, Tuple


class MaterialShapeId(str, Enum):
    """Material 3 Expressive shape identifiers.

    This is a small subset required by the M3 Expressive loading indicator.
    """

    SOFT_BURST = "soft_burst"
    COOKIE_9_SIDED = "cookie_9_sided"
    PENTAGON = "pentagon"
    PILL = "pill"
    SUNNY = "sunny"
    COOKIE_4_SIDED = "cookie_4_sided"
    OVAL = "oval"


DEFAULT_LOADING_INDICATOR_SEQUENCE: Tuple[MaterialShapeId, ...] = (
    MaterialShapeId.SOFT_BURST,
    MaterialShapeId.COOKIE_9_SIDED,
    MaterialShapeId.PENTAGON,
    MaterialShapeId.PILL,
    MaterialShapeId.SUNNY,
    MaterialShapeId.COOKIE_4_SIDED,
    MaterialShapeId.OVAL,
)


Point = Tuple[float, float]


@dataclass(frozen=True)
class ShapeParams:
    """Parameters for a polar sampling shape."""

    a: float = 1.0
    b: float = 1.0
    exp: float = 2.0
    ripple_k: int = 0
    ripple_amp: float = 0.0
    phase: float = 0.0


_SHAPE_PARAMS: Dict[MaterialShapeId, ShapeParams] = {
    MaterialShapeId.SOFT_BURST: ShapeParams(a=1.0, b=1.0, exp=1.6, ripple_k=12, ripple_amp=0.10, phase=0.2),
    MaterialShapeId.COOKIE_9_SIDED: ShapeParams(a=1.0, b=1.0, exp=2.2, ripple_k=9, ripple_amp=0.14, phase=0.0),
    MaterialShapeId.PENTAGON: ShapeParams(a=1.0, b=1.0, exp=4.0, ripple_k=5, ripple_amp=0.06, phase=0.0),
    MaterialShapeId.PILL: ShapeParams(a=1.25, b=0.78, exp=6.5, ripple_k=0, ripple_amp=0.0, phase=0.0),
    MaterialShapeId.SUNNY: ShapeParams(a=1.0, b=1.0, exp=2.0, ripple_k=8, ripple_amp=0.22, phase=0.0),
    MaterialShapeId.COOKIE_4_SIDED: ShapeParams(a=1.0, b=1.0, exp=5.5, ripple_k=4, ripple_amp=0.10, phase=0.0),
    MaterialShapeId.OVAL: ShapeParams(a=1.15, b=0.72, exp=2.0, ripple_k=0, ripple_amp=0.0, phase=0.0),
}


def _superellipse_point(theta: float, *, a: float, b: float, exp: float) -> Point:
    """Return a point on a superellipse.

    The shape is normalized around the origin.

    exp=2 yields an ellipse. Higher values approach a rectangle.
    """

    n = max(0.2, float(exp))
    ct = cos(theta)
    st = sin(theta)

    x = a * copysign(abs(ct) ** (2.0 / n), ct)
    y = b * copysign(abs(st) ** (2.0 / n), st)
    return (x, y)


def _apply_ripple(theta: float, *, k: int, amp: float, phase: float) -> float:
    if k <= 0 or amp == 0.0:
        return 1.0
    return 1.0 + float(amp) * sin(float(k) * theta + float(phase) * 2.0 * pi)


def sample_shape_points(
    shape_id: MaterialShapeId,
    *,
    n_points: int,
) -> List[Point]:
    """Return a closed shape as a list of points.

    Points are centered at (0,0) in a roughly unit scale.

    Args:
        shape_id: Shape identifier.
        n_points: Number of points to sample (>= 3).

    Returns:
        List of (x,y) points.
    """

    n = int(n_points)
    if n < 3:
        raise ValueError("n_points must be >= 3")

    params = _SHAPE_PARAMS.get(shape_id)
    if params is None:
        raise ValueError(f"Unknown shape id: {shape_id}")

    out: List[Point] = []
    for i in range(n):
        theta = 2.0 * pi * (i / n)
        ripple = _apply_ripple(theta, k=params.ripple_k, amp=params.ripple_amp, phase=params.phase)
        x, y = _superellipse_point(theta, a=params.a, b=params.b, exp=params.exp)
        out.append((x * ripple, y * ripple))

    _normalize_points_in_place(out)
    return out


def _normalize_points_in_place(points: List[Point]) -> None:
    """Normalize points to fit within [-1, 1] range."""

    if not points:
        return
    max_abs = 0.0
    for x, y in points:
        max_abs = max(max_abs, abs(x), abs(y))
    if max_abs <= 1e-9:
        return
    inv = 1.0 / max_abs
    for idx, (x, y) in enumerate(points):
        points[idx] = (x * inv, y * inv)


def lerp_points(a: Sequence[Point], b: Sequence[Point], t: float) -> List[Point]:
    """Linearly interpolate two point lists."""

    if len(a) != len(b):
        raise ValueError("Point lists must have the same length")
    tt = max(0.0, min(1.0, float(t)))
    out: List[Point] = []
    for (ax, ay), (bx, by) in zip(a, b):
        out.append((ax + (bx - ax) * tt, ay + (by - ay) * tt))
    return out


def iter_segments_circular(items: Sequence[MaterialShapeId]) -> Iterable[Tuple[MaterialShapeId, MaterialShapeId]]:
    if not items:
        return
    for i in range(len(items)):
        yield (items[i], items[(i + 1) % len(items)])
