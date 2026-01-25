"""Common enumerations for scroll handling."""

from __future__ import annotations

from enum import Enum


class ScrollDirection(str, Enum):
    """Represents the axis along which scrolling occurs."""

    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"

    @property
    def is_vertical(self) -> bool:
        return self is ScrollDirection.VERTICAL

    @property
    def is_horizontal(self) -> bool:
        return self is ScrollDirection.HORIZONTAL


class ScrollPhysics(str, Enum):
    """Available physics/behavior presets for scroll interactions."""

    CLAMP = "clamp"
    NEVER = "never"


__all__ = ["ScrollDirection", "ScrollPhysics"]
