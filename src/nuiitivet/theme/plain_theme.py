"""Plain Theme implementation.

This module defines the PlainThemeData, PlainColorRole, and PlainTheme factory
for the default design-system-agnostic theme.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING

from nuiitivet.scrolling.scrollbar_theme_data import ScrollbarThemeData
from nuiitivet.theme.theme import Theme

if TYPE_CHECKING:
    from nuiitivet.theme.types import ColorLike


@dataclass(frozen=True)
class PlainThemeData:
    """Theme data for the Plain design system."""

    surface: str
    on_surface: str
    outline: str
    scrim: str
    spacing: int = 8

    def copy_with(self, **kwargs) -> "PlainThemeData":
        return replace(self, **kwargs)


class PlainColorRole(Enum):
    """Plain Color Roles."""

    SURFACE = "surface"
    ON_SURFACE = "on_surface"
    OUTLINE = "outline"
    SCRIM = "scrim"

    def resolve(self, theme: "Theme | None" = None) -> ColorLike | None:
        """Resolve this token into a concrete ColorLike."""
        if theme is None:
            return None
        theme_data = theme.extension(PlainThemeData)
        if theme_data is None:
            return None

        if self == PlainColorRole.SURFACE:
            return theme_data.surface
        elif self == PlainColorRole.ON_SURFACE:
            return theme_data.on_surface
        elif self == PlainColorRole.OUTLINE:
            return theme_data.outline
        elif self == PlainColorRole.SCRIM:
            return theme_data.scrim
        return None


def _plain_scrollbar_theme_data() -> ScrollbarThemeData:
    """Default scrollbar palette for the Plain design system.

    The Plain theme has no accent color, so every slot maps onto
    ``PlainColorRole.ON_SURFACE`` (with differing alpha) as tokens. Resolving at
    paint time keeps the scrollbar in sync when switching between the light and
    dark Plain themes.
    """
    return ScrollbarThemeData(
        track=(PlainColorRole.ON_SURFACE, 0.12),
        thumb=(PlainColorRole.ON_SURFACE, 0.70),
        thumb_hover=(PlainColorRole.ON_SURFACE, 0.90),
        thumb_active=(PlainColorRole.ON_SURFACE, 1.0),
    )


class PlainTheme:
    """Factory for creating Themes with Plain configuration."""

    @staticmethod
    def light() -> Theme:
        """Create a light Plain theme."""
        data = PlainThemeData(
            surface="#FFFFFF",
            on_surface="#000000",
            outline="#79747E",
            scrim="#000000",
        )
        return Theme(
            mode="light",
            extensions=[data, _plain_scrollbar_theme_data()],
            name="plain-light",
        )

    @staticmethod
    def dark() -> Theme:
        """Create a dark Plain theme."""
        data = PlainThemeData(
            surface="#121212",
            on_surface="#FFFFFF",
            outline="#938F99",
            scrim="#000000",
        )
        return Theme(
            mode="dark",
            extensions=[data, _plain_scrollbar_theme_data()],
            name="plain-dark",
        )
