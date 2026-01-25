from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple, TYPE_CHECKING

from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from ...theme import Theme


@dataclass(frozen=True)
class TextFieldStyle:
    """Style configuration for TextField (M3-compliant)."""

    # Container
    container_color: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGHEST

    # Border / Indicator
    indicator_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    indicator_width: float = 1.0
    focused_indicator_color: ColorSpec = ColorRole.PRIMARY
    focused_indicator_width: float = 2.0
    error_indicator_color: ColorSpec = ColorRole.ERROR

    # Text
    text_color: ColorSpec = ColorRole.ON_SURFACE
    label_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    focused_label_color: ColorSpec = ColorRole.PRIMARY
    error_label_color: ColorSpec = ColorRole.ERROR

    # Cursor & Selection
    cursor_color: ColorSpec = ColorRole.PRIMARY
    error_cursor_color: ColorSpec = ColorRole.ERROR
    selection_color: ColorSpec = ColorRole.PRIMARY_CONTAINER  # Usually with opacity

    # Shape
    border_radius: float = 4.0  # Top corners for filled, all for outlined

    # Layout
    content_padding: Tuple[int, int, int, int] = (16, 16, 16, 16)  # L, T, R, B

    def copy_with(self, **changes) -> "TextFieldStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    @classmethod
    def filled(cls) -> "TextFieldStyle":
        """Default M3 Filled TextField style."""
        return cls(
            container_color=ColorRole.SURFACE_CONTAINER_HIGHEST,
            indicator_color=ColorRole.ON_SURFACE_VARIANT,
            border_radius=4.0,
            content_padding=(16, 8, 16, 8),  # Adjusted for label
        )

    @classmethod
    def outlined(cls) -> "TextFieldStyle":
        """Default M3 Outlined TextField style."""
        return cls(
            container_color=(0, 0, 0, 0),  # Transparent
            indicator_color=ColorRole.OUTLINE,
            border_radius=4.0,
            content_padding=(16, 16, 16, 16),
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "filled") -> "TextFieldStyle":
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        v = (variant or "").lower()

        if theme_data:
            if v == "filled":
                return theme_data.filled_text_field_style
            if v == "outlined":
                return theme_data.outlined_text_field_style

        # Fallback
        if v == "filled":
            return cls.filled()
        if v == "outlined":
            return cls.outlined()

        return cls.filled()
