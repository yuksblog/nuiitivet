"""Badge style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class SmallBadgeStyle:
    """Immutable style for small dot badge widgets."""

    background_color: ColorSpec = ColorRole.ERROR
    width: int = 6
    height: int = 6
    corner_radius: float = 3.0

    def copy_with(self, **changes) -> "SmallBadgeStyle":
        """Return a copy of this style with overridden fields."""
        return replace(self, **changes)


@dataclass(frozen=True)
class LargeBadgeStyle:
    """Immutable style for large text/count badge widgets."""

    background_color: ColorSpec = ColorRole.ERROR
    content_color: ColorSpec = ColorRole.ON_ERROR
    height: int = 16
    padding: tuple[int, int, int, int] = (4, 0, 4, 0)
    corner_radius: float = 8.0
    font_size: int = 11

    def copy_with(self, **changes) -> "LargeBadgeStyle":
        """Return a copy of this style with overridden fields."""
        return replace(self, **changes)
