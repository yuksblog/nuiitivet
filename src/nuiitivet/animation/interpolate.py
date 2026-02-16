"""Interpolation helpers for animation and layout values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


def lerp(begin: float, end: float, t: float) -> float:
    """Linearly interpolate between ``begin`` and ``end`` by ``t``."""
    b = float(begin)
    e = float(end)
    return b + (e - b) * float(t)


def lerp_int(begin: int, end: int, t: float) -> int:
    """Linearly interpolate between integers and round to nearest int."""
    return int(round(lerp(float(begin), float(end), t)))


@dataclass(frozen=True)
class Rect:
    """Immutable rectangle representation.

    Attributes:
        x: X coordinate of the top-left corner.
        y: Y coordinate of the top-left corner.
        width: Width of the rectangle.
        height: Height of the rectangle.
    """

    x: float
    y: float
    width: float
    height: float

    def round(self) -> Rect:
        """Return a new Rect with rounded integer coordinates."""
        return Rect(x=round(self.x), y=round(self.y), width=round(self.width), height=round(self.height))

    def to_int_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to ``(x, y, width, height)`` tuple of integers."""
        return (int(round(self.x)), int(round(self.y)), int(round(self.width)), int(round(self.height)))

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """Convert to ``(x, y, width, height)`` tuple of floats."""
        return (self.x, self.y, self.width, self.height)

    @staticmethod
    def from_tuple(t: Tuple[float, float, float, float]) -> Rect:
        """Create a Rect from a ``(x, y, width, height)`` tuple."""
        return Rect(x=t[0], y=t[1], width=t[2], height=t[3])


def lerp_rect(begin: Rect, end: Rect, t: float) -> Rect:
    """Linearly interpolate between rectangles."""
    return Rect(
        x=lerp(begin.x, end.x, t),
        y=lerp(begin.y, end.y, t),
        width=lerp(begin.width, end.width, t),
        height=lerp(begin.height, end.height, t),
    )


__all__ = ["Rect", "lerp", "lerp_int", "lerp_rect"]
