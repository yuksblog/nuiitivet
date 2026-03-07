"""Toolbar widget style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Optional

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

ToolbarColorScheme = Literal["standard", "vibrant"]


@dataclass(frozen=True)
class ToolbarStyle:
    """Immutable style for Material toolbar widgets.

    Args:
        color_scheme: Toolbar color scheme variant.
        background: Toolbar container background color.
        foreground: Recommended foreground color for icon actions.
        container_height: Visual container height in pixels.
        content_padding: Internal content insets.
        item_gap: Gap between action buttons.
        corner_radius: Container corner radius in pixels.
        border_color: Optional border color.
        border_width: Border width in pixels.
        elevation: Elevation level for shadow rendering.
    """

    color_scheme: ToolbarColorScheme = "standard"
    background: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGHEST
    foreground: ColorSpec = ColorRole.ON_SURFACE
    container_height: int = 64
    content_padding: tuple[int, int, int, int] = (16, 0, 16, 0)
    item_gap: int = 8
    corner_radius: int = 0
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0
    elevation: float = 0.0

    def copy_with(self, **changes) -> "ToolbarStyle":
        """Return a copy of this style with changed fields."""
        return replace(self, **changes)

    @classmethod
    def standard(cls) -> "ToolbarStyle":
        """Return the standard toolbar style."""
        return cls(
            color_scheme="standard",
            background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            foreground=ColorRole.ON_SURFACE,
            container_height=64,
            content_padding=(16, 0, 16, 0),
            item_gap=8,
            corner_radius=0,
            border_color=None,
            border_width=0.0,
            elevation=0.0,
        )

    @classmethod
    def vibrant(cls) -> "ToolbarStyle":
        """Return the vibrant toolbar style."""
        return cls(
            color_scheme="vibrant",
            background=ColorRole.PRIMARY_CONTAINER,
            foreground=ColorRole.ON_PRIMARY_CONTAINER,
            container_height=64,
            content_padding=(16, 0, 16, 0),
            item_gap=8,
            corner_radius=0,
            border_color=None,
            border_width=0.0,
            elevation=0.0,
        )


__all__ = ["ToolbarColorScheme", "ToolbarStyle"]
