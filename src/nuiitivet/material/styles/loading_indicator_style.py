"""LoadingIndicatorStyle definition for M3 Expressive loading indicator."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Sequence, Tuple, Union, TYPE_CHECKING

from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec
from nuiitivet.animation.motion import Motion
from nuiitivet.material.motion import EXPRESSIVE_SLOW_SPATIAL

if TYPE_CHECKING:
    from ...theme import Theme
    from ..shapes import MaterialShapeId

PaddingLike = Union[int, Tuple[int, int, int, int]]


@dataclass(frozen=True)
class LoadingIndicatorStyle:
    """Style for LoadingIndicator widgets (M3-compliant).

    The dataclass provides style configuration for the M3 Expressive loading indicator,
    including colors, sizing, animation parameters, and optional container styling
    for contained variants.
    """

    # Colors
    foreground: ColorSpec = ColorRole.PRIMARY
    background: Optional[ColorSpec] = None  # For contained variant

    # Sizing
    # M3 spec: 48dp container with 38dp active indicator
    active_size_ratio: float = 38.0 / 48.0

    # Animation
    # Default motion uses Expressive Default Effects.
    # Note: The duration is defined by the motion token (approx 0.2s for EXPRESSIVE_DEFAULT_EFFECTS).
    motion: Motion = EXPRESSIVE_SLOW_SPATIAL
    shapes: Sequence["MaterialShapeId"] = ()  # Set to DEFAULT_LOADING_INDICATOR_SEQUENCE in default()

    # Container styling (for contained variant)
    elevation: float = 0.0
    corner_radius: int = 24

    # Layout
    padding: PaddingLike = 0

    def copy_with(self, **changes) -> "LoadingIndicatorStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict:
        """Resolve ColorRole to concrete color values."""
        from ...theme.resolver import resolve_color_to_rgba

        return {
            "foreground": resolve_color_to_rgba(self.foreground, theme=theme) if self.foreground else None,
            "background": resolve_color_to_rgba(self.background, theme=theme) if self.background else None,
        }

    @classmethod
    def default(cls) -> "LoadingIndicatorStyle":
        """Standard loading indicator (no background)."""
        from ..shapes import DEFAULT_LOADING_INDICATOR_SEQUENCE

        return cls(shapes=DEFAULT_LOADING_INDICATOR_SEQUENCE)

    @classmethod
    def contained(cls) -> "LoadingIndicatorStyle":
        """Contained loading indicator with background."""
        from ..shapes import DEFAULT_LOADING_INDICATOR_SEQUENCE

        return cls(
            background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            elevation=1.0,
            shapes=DEFAULT_LOADING_INDICATOR_SEQUENCE,
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "default") -> "LoadingIndicatorStyle":
        """Get style from theme for a given variant.

        Args:
            theme: Theme to load style from.
            variant: Variant name ("default" or "contained").

        Returns:
            LoadingIndicatorStyle from theme or default.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        v = (variant or "").lower()

        if theme_data:
            if v in ("contained", "container"):
                return theme_data.contained_loading_indicator_style
            return theme_data.loading_indicator_style

        # Fallback
        if v in ("contained", "container"):
            return cls.contained()
        return cls.default()


__all__ = ["LoadingIndicatorStyle"]
