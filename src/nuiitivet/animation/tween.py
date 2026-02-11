"""Tween implementation for animations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, Generic, Tuple

T = TypeVar("T")


class Tween(Generic[T]):
    """Base class for value interpolation.

    If used directly, it acts as an identity transformation (0.0->0.0, 1.0->1.0).
    """

    def transform(self, t: float) -> T:
        """Transforms the time t (0.0 to 1.0) to a value of type T."""
        return t  # type: ignore


class LerpTween(Tween[T]):
    """Tween that interpolates between two values."""

    def __init__(self, begin: T, end: T):
        self.begin = begin
        self.end = end

    def lerp(self, t: float) -> T:
        """Linear interpolate between begin and end."""
        # This assumes T supports standard operator overload (float, int, etc)
        # For complex types (Color, Rect) subclasses should override.
        return self.begin + (self.end - self.begin) * t  # type: ignore

    def transform(self, t: float) -> T:
        if t == 0.0:
            return self.begin
        if t == 1.0:
            return self.end
        return self.lerp(t)


class IntTween(LerpTween[int]):
    """Tween for integer values."""

    def lerp(self, t: float) -> int:
        return int(round(self.begin + (self.end - self.begin) * t))


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
        """Convert to (x, y, width, height) tuple of integers."""
        return (int(round(self.x)), int(round(self.y)), int(round(self.width)), int(round(self.height)))

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """Convert to (x, y, width, height) tuple of floats."""
        return (self.x, self.y, self.width, self.height)

    @staticmethod
    def from_tuple(t: Tuple[float, float, float, float]) -> Rect:
        """Create a Rect from a (x, y, width, height) tuple."""
        return Rect(x=t[0], y=t[1], width=t[2], height=t[3])


class RectTween(LerpTween[Rect]):
    """Tween for rectangle interpolation."""

    def lerp(self, t: float) -> Rect:
        """Linear interpolate between begin and end rectangles."""
        b, e = self.begin, self.end
        return Rect(
            x=b.x + (e.x - b.x) * t,
            y=b.y + (e.y - b.y) * t,
            width=b.width + (e.width - b.width) * t,
            height=b.height + (e.height - b.height) * t,
        )
