"""Transition patterns for composable animations.

Maps a progress value (0.0 to 1.0) to visual properties.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class TransitionVisuals:
    """Collection of visual properties affected by transitions."""

    opacity: float | None = None
    scale_x: float | None = None
    scale_y: float | None = None
    translate_x: float | None = None
    translate_y: float | None = None

    # Allows merging visuals from multiple patterns
    def merge(self, other: TransitionVisuals) -> TransitionVisuals:
        return TransitionVisuals(
            opacity=other.opacity if other.opacity is not None else self.opacity,
            scale_x=other.scale_x if other.scale_x is not None else self.scale_x,
            scale_y=other.scale_y if other.scale_y is not None else self.scale_y,
            translate_x=other.translate_x if other.translate_x is not None else self.translate_x,
            translate_y=other.translate_y if other.translate_y is not None else self.translate_y,
        )


@runtime_checkable
class TransitionPattern(Protocol):
    """A functional unit that maps progress to visual properties."""

    def resolve(self, progress: float) -> TransitionVisuals:
        """Resolve visual properties at the given progress (0.0 to 1.0)."""
        ...

    def __or__(self, other: TransitionPattern) -> TransitionPattern:
        """Compose this pattern with another."""
        ...


class CompositePattern:
    """Combines two transition patterns."""

    def __init__(self, first: TransitionPattern, second: TransitionPattern) -> None:
        self.first = first
        self.second = second

    def resolve(self, progress: float) -> TransitionVisuals:
        v1 = self.first.resolve(progress)
        v2 = self.second.resolve(progress)
        return v1.merge(v2)

    def __or__(self, other: TransitionPattern) -> TransitionPattern:
        return CompositePattern(self, other)


class FadePattern:
    """Controls opacity based on progress."""

    def __init__(self, start_alpha: float = 0.0, end_alpha: float = 1.0) -> None:
        self.start_alpha = start_alpha
        self.end_alpha = end_alpha

    def resolve(self, progress: float) -> TransitionVisuals:
        opacity = self.start_alpha + (self.end_alpha - self.start_alpha) * progress
        return TransitionVisuals(opacity=opacity)

    def __or__(self, other: TransitionPattern) -> TransitionPattern:
        return CompositePattern(self, other)


class SlidePattern:
    """Controls translation based on progress."""

    def __init__(
        self,
        start_x: float = 0.0,
        start_y: float = 0.0,
        end_x: float = 0.0,
        end_y: float = 0.0,
    ) -> None:
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y

    def resolve(self, progress: float) -> TransitionVisuals:
        tx = self.start_x + (self.end_x - self.start_x) * progress
        ty = self.start_y + (self.end_y - self.start_y) * progress
        return TransitionVisuals(translate_x=tx, translate_y=ty)

    def __or__(self, other: TransitionPattern) -> TransitionPattern:
        return CompositePattern(self, other)


class ScalePattern:
    """Controls scale based on progress."""

    def __init__(
        self,
        start_scale_x: float = 0.8,
        start_scale_y: float = 0.8,
        end_scale_x: float = 1.0,
        end_scale_y: float = 1.0,
    ) -> None:
        self.start_scale_x = start_scale_x
        self.start_scale_y = start_scale_y
        self.end_scale_x = end_scale_x
        self.end_scale_y = end_scale_y

    def resolve(self, progress: float) -> TransitionVisuals:
        sx = self.start_scale_x + (self.end_scale_x - self.start_scale_x) * progress
        sy = self.start_scale_y + (self.end_scale_y - self.start_scale_y) * progress
        return TransitionVisuals(scale_x=sx, scale_y=sy)

    def __or__(self, other: TransitionPattern) -> TransitionPattern:
        return CompositePattern(self, other)
