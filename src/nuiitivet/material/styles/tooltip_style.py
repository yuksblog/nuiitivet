"""Tooltip style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


@dataclass(frozen=True)
class TooltipStyle:
    """Immutable style for Material Design 3 plain tooltip widgets."""

    container_color: ColorSpec = ColorRole.INVERSE_SURFACE
    content_color: ColorSpec = ColorRole.INVERSE_ON_SURFACE
    corner_radius: int = 4
    horizontal_padding: int = 8
    vertical_padding: int = 4
    min_height: int = 24
    max_width: int = 320
    elevation: float = 0.0
    elevation_color: ColorSpec = ColorRole.SHADOW
    text_size: int = 12
    line_height: int = 16

    def copy_with(self, **changes) -> "TooltipStyle":
        """Return a copy of this style with selected fields overridden."""
        return replace(self, **changes)

    @classmethod
    def standard(cls) -> "TooltipStyle":
        """Return the standard plain tooltip style."""
        return cls()

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "standard") -> "TooltipStyle":
        """Resolve TooltipStyle from theme.

        Args:
            theme: Theme instance (reserved for future extension).
            variant: Currently supports ``"standard"``.

        Returns:
            Resolved ``TooltipStyle``.
        """
        _ = theme
        _ = variant
        return cls.standard()


@dataclass(frozen=True)
class RichTooltipStyle:
    """Immutable style for Material Design 3 rich tooltip widgets."""

    container_color: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGHEST
    supporting_text_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    subhead_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    action_color: ColorSpec = ColorRole.PRIMARY
    corner_radius: int = 12
    horizontal_padding: int = 16
    top_padding: int = 12
    bottom_padding: int = 8
    min_width: int = 160
    max_width: int = 320
    elevation: float = 2.0
    elevation_color: ColorSpec = ColorRole.SHADOW
    subhead_text_size: int = 14
    supporting_text_size: int = 14

    def copy_with(self, **changes) -> "RichTooltipStyle":
        """Return a copy of this style with selected fields overridden."""
        return replace(self, **changes)

    @classmethod
    def standard(cls) -> "RichTooltipStyle":
        """Return the standard rich tooltip style."""
        return cls()

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "standard") -> "RichTooltipStyle":
        """Resolve RichTooltipStyle from theme.

        Args:
            theme: Theme instance (reserved for future extension).
            variant: Currently supports ``"standard"``.

        Returns:
            Resolved ``RichTooltipStyle``.
        """
        _ = theme
        _ = variant
        return cls.standard()


__all__ = ["TooltipStyle", "RichTooltipStyle"]
