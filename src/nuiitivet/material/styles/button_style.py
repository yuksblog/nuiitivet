"""Canonical ButtonStyle definition.

This module provides the canonical `ButtonStyle` dataclass used by the
`nuiitivet.material.styles` package. Older import paths are kept working via
the trivial re-export in `nuiitivet.material.styles.button`.
"""

from dataclasses import dataclass, replace
from typing import Optional, Union, TYPE_CHECKING

from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

PaddingLike = Union[int, tuple[int, int, int, int]]

if TYPE_CHECKING:
    from ...theme import Theme


@dataclass(frozen=True)
class ButtonStyle:
    """Immutable style for Button widgets (M3-compliant).

    The dataclass mirrors the legacy API expected by widgets during the
    refactor and provides convenience constructors for standard variants.
    """

    # Container properties
    background: Optional[ColorSpec] = None
    foreground: Optional[ColorSpec] = None
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0
    corner_radius: int = 20

    # Sizing
    # Container height (visual), separate from the minimum touch target.
    container_height: int = 40
    # Container internal insets.
    padding: PaddingLike = (16, 0, 16, 0)
    spacing: int = 8
    min_width: int = 64
    min_height: int = 48

    # Elevation (for elevated buttons)
    elevation: float = 0.0

    # State overlay (hover/press)
    overlay_color: Optional[ColorSpec] = None
    overlay_alpha: float = 0.0

    def copy_with(self, **changes) -> "ButtonStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict:
        """Resolve ColorRole to concrete color values using the rendering
        helpers.
        """
        from ...theme.resolver import resolve_color_to_rgba

        return {
            "background": resolve_color_to_rgba(self.background, theme=theme) if self.background else None,
            "foreground": resolve_color_to_rgba(self.foreground, theme=theme) if self.foreground else None,
            "border_color": resolve_color_to_rgba(self.border_color, theme=theme) if self.border_color else None,
            "overlay_color": resolve_color_to_rgba(self.overlay_color, theme=theme) if self.overlay_color else None,
        }

    def resolve(self, theme: "Theme | None" = None) -> dict:
        """Compatibility resolver returning a dict similar to the legacy
        ButtonStyle.resolve() used by widgets.

        Keys: background, foreground, border_color, corner_radius, padding,
        min_size, text_style, overlay
        """
        colors = self.resolve_colors(theme=theme)
        resolved = {
            "background": colors.get("background"),
            "foreground": colors.get("foreground"),
            "border_color": colors.get("border_color"),
            "corner_radius": self.corner_radius,
            "padding": self.padding,
            "spacing": getattr(self, "spacing", 8),
            "min_size": (self.min_width, self.min_height),
            "text_style": None,
        }

        if self.overlay_color is not None:
            try:
                resolved["overlay"] = (self.overlay_color, float(self.overlay_alpha or 0.0))
            except Exception:
                resolved["overlay"] = None
        else:
            resolved["overlay"] = None

        return resolved

    @classmethod
    def filled(cls) -> "ButtonStyle":
        return cls(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            border_width=0.0,
            corner_radius=20,
            container_height=40,
            padding=(16, 0, 16, 0),
            elevation=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.08,
        )

    @classmethod
    def outlined(cls) -> "ButtonStyle":
        return cls(
            background=None,
            foreground=ColorRole.PRIMARY,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            corner_radius=20,
            container_height=40,
            padding=(16, 0, 16, 0),
            elevation=0.0,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.08,
        )

    @classmethod
    def text(cls) -> "ButtonStyle":
        return cls(
            background=None,
            foreground=ColorRole.PRIMARY,
            border_width=0.0,
            corner_radius=20,
            container_height=40,
            padding=(16, 0, 16, 0),
            min_width=48,
            min_height=48,
            elevation=0.0,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.12,
        )

    @classmethod
    def elevated(cls) -> "ButtonStyle":
        return cls(
            background=ColorRole.SURFACE,
            foreground=ColorRole.PRIMARY,
            border_width=0.0,
            corner_radius=20,
            container_height=40,
            padding=(16, 0, 16, 0),
            elevation=1.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.06,
        )

    @classmethod
    def tonal(cls) -> "ButtonStyle":
        return cls(
            background=ColorRole.SECONDARY_CONTAINER,
            foreground=ColorRole.ON_SECONDARY_CONTAINER,
            border_width=0.0,
            corner_radius=20,
            container_height=40,
            padding=(16, 0, 16, 0),
            elevation=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.08,
        )

    @classmethod
    def fab(cls) -> "ButtonStyle":
        return cls(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            border_width=0.0,
            corner_radius=28,
            padding=(8, 8, 8, 8),
            container_height=56,
            min_width=56,
            min_height=56,
            elevation=6.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.08,
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "filled") -> "ButtonStyle":
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        v = (variant or "").lower()

        if theme_data:
            if v == "filled":
                return theme_data.filled_button_style
            if v == "text":
                return theme_data.text_button_style
            if v == "outlined":
                return theme_data.outlined_button_style
            if v == "elevated":
                return theme_data.elevated_button_style
            if v in ("tonal", "filled_tonal", "filledtonal"):
                return theme_data.tonal_button_style
            if v in ("fab", "floating_action_button"):
                return theme_data.fab_style

        # Fallback if no theme data or unknown variant (though unknown variant logic is same as above)
        if v == "filled":
            return cls.filled()
        if v == "text":
            return cls.text()
        if v == "outlined":
            return cls.outlined()
        if v == "elevated":
            return cls.elevated()
        if v in ("tonal", "filled_tonal", "filledtonal"):
            return cls.tonal()
        if v in ("fab", "floating_action_button"):
            return cls.fab()

        return cls.filled()


__all__ = ["ButtonStyle"]
