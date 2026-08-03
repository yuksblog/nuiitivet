"""Toolbar widget style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Optional, TYPE_CHECKING

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme

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

    @classmethod
    def preset(cls, variant: ToolbarColorScheme = "standard") -> "ToolbarStyle":
        """Return the framework preset for ``variant``, ignoring any theme.

        This is what a toolbar renders with before it is mounted, and what
        :meth:`from_theme` falls back to when no Material theme is installed.

        Args:
            variant: One of ``standard`` or ``vibrant``. Unknown values fall
                back to ``standard``.

        Returns:
            The variant preset style.
        """
        if str(variant or "standard").lower() == "vibrant":
            return cls.vibrant()
        return cls.standard()

    @classmethod
    def from_theme(cls, theme: "Theme", variant: ToolbarColorScheme = "standard") -> "ToolbarStyle":
        """Resolve the toolbar style from ``theme``.

        Args:
            theme: Theme instance.
            variant: One of ``standard`` or ``vibrant``. Only ``standard`` is
                carried by :class:`MaterialThemeData`; ``vibrant`` is an
                explicit opt-in and always returns its preset.

        Returns:
            Resolved toolbar style.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        variant_name = str(variant or "standard").lower()
        if variant_name == "standard":
            theme_data = theme.extension(MaterialThemeData)
            if theme_data is not None:
                return theme_data.toolbar_style
        return cls.preset(variant)


__all__ = ["ToolbarColorScheme", "ToolbarStyle"]
