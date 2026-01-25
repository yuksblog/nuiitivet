"""Canonical CardStyle definition.

This module provides the canonical `CardStyle` dataclass used by the
`nuiitivet.material.styles` package.
"""

from dataclasses import dataclass, replace
from typing import Optional, Union, TYPE_CHECKING

from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from ...theme import Theme


@dataclass(frozen=True)
class CardStyle:
    """Immutable style for Card widgets (M3-compliant)."""

    # Container properties
    background: Optional[ColorSpec] = None
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0
    border_radius: Union[float, tuple[float, float, float, float]] = 12.0

    # Elevation
    elevation: float = 0.0
    shadow_color: Optional[ColorSpec] = None

    def copy_with(self, **changes) -> "CardStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict:
        """Resolve ColorRole to concrete color values."""
        from ...theme.resolver import resolve_color_to_rgba

        return {
            "background": resolve_color_to_rgba(self.background, theme=theme) if self.background else None,
            "border_color": resolve_color_to_rgba(self.border_color, theme=theme) if self.border_color else None,
            "shadow_color": resolve_color_to_rgba(self.shadow_color, theme=theme) if self.shadow_color else None,
        }

    @classmethod
    def elevated(cls) -> "CardStyle":
        """Create a default style for ElevatedCard."""
        return cls(
            background=ColorRole.SURFACE,
            elevation=1.0,
            shadow_color=ColorRole.SHADOW,
            border_radius=12.0,
        )

    @classmethod
    def filled(cls) -> "CardStyle":
        """Create a default style for FilledCard."""
        return cls(
            background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            elevation=0.0,
            border_radius=12.0,
        )

    @classmethod
    def outlined(cls) -> "CardStyle":
        """Create a default style for OutlinedCard."""
        return cls(
            background=ColorRole.SURFACE,
            elevation=0.0,
            border_width=1.0,
            border_color=ColorRole.OUTLINE,
            border_radius=12.0,
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "filled") -> "CardStyle":
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        v = (variant or "").lower()

        if theme_data:
            if v == "filled":
                return theme_data.filled_card_style
            if v == "outlined":
                return theme_data.outlined_card_style
            if v == "elevated":
                return theme_data.elevated_card_style

        # Fallback
        if v == "filled":
            return cls.filled()
        if v == "outlined":
            return cls.outlined()
        if v == "elevated":
            return cls.elevated()

        return cls.filled()
