"""Icon widget style (moved from `nuiitivet.ui.styles.icon`).

This module was moved into the flat `nuiitivet.material.styles` package. It
uses absolute imports to avoid fragile relative-dot counts during the
reorg.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Tuple

from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


@dataclass(frozen=True)
class IconStyle:
    """Immutable style for Icon widgets (M3準拠).

    Material Design 3 Icon specifications:
    - Default size: 24dp
    - Default color: ON_SURFACE
    - Font family priority: Material Symbols → Material Icons
    """

    # Size
    default_size: int = 24
    padding: int = 0

    # Family (outlined, rounded, sharp, icons)
    family: str = "outlined"

    # Colors
    color: ColorSpec = ColorRole.ON_SURFACE

    # Material Symbols font family priority
    # Try "outlined" style first, then fall back to legacy "icons"
    font_family_priority: Tuple[str, ...] = (
        "Material Symbols Outlined",
        "Material Symbols Rounded",
        "Material Symbols Sharp",
        "Material Icons",
    )

    # Material style mapping (for font family selection)
    style_to_family: dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self):
        """Initialize style_to_family mapping."""
        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(
            self,
            "style_to_family",
            {
                "outlined": "Material Symbols Outlined",
                "rounded": "Material Symbols Rounded",
                "sharp": "Material Symbols Sharp",
                "icons": "Material Icons",
            },
        )

    def copy_with(self, **changes) -> "IconStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_color(self, color: ColorSpec, theme: "Theme | None" = None) -> tuple[int, int, int, int]:
        """Resolve ColorRole to an (r,g,b,a) tuple using the theme resolver."""
        from nuiitivet.theme.resolver import resolve_color_to_rgba

        return resolve_color_to_rgba(color, theme=theme)

    def get_font_family(self, style: str) -> str:
        """Get font family name for given style."""
        return self.style_to_family.get(style, self.font_family_priority[0])


__all__ = ["IconStyle"]
