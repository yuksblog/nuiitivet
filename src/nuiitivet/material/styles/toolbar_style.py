"""Toolbar widget style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Optional, TYPE_CHECKING

from nuiitivet.material.styles.button_size import FabSize
from nuiitivet.material.styles.button_style import ButtonStyle, IconButtonStyle, IconToggleButtonStyle
from nuiitivet.material.styles.fab_style import FabStyle
from nuiitivet.material.styles.toggle_button_style import ToggleButtonStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme

ToolbarColorScheme = Literal["standard", "vibrant"]


@dataclass(frozen=True)
class ToolbarStyle:
    """Immutable style for Material toolbar widgets.

    Presets: :meth:`standard`, :meth:`vibrant`. The ``*_style`` methods
    derive the styles a toolbar pushes onto the buttons it hosts.

    Attributes:
        color_scheme: Toolbar color scheme variant.
        background: Toolbar container background color.
        foreground: Icon and label color of the toolbar's buttons.
        selected_background: Container color of a selected toggle button.
        selected_foreground: Icon and label color of a selected toggle button.
        container_height: Visual container height in pixels.
        content_insets: Internal content insets.
        item_gap: Gap between action buttons.
        fab_gap: Gap between a floating toolbar and the FAB beside it.
        corner_radius: Container corner radius in pixels.
        border_color: Optional border color.
        border_width: Border width in pixels.
        elevation: Elevation level for shadow rendering.
    """

    color_scheme: ToolbarColorScheme = "standard"
    background: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGHEST
    foreground: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    selected_background: ColorSpec = ColorRole.SECONDARY_CONTAINER
    selected_foreground: ColorSpec = ColorRole.ON_SECONDARY_CONTAINER
    container_height: int = 64
    content_insets: tuple[int, int, int, int] = (16, 0, 16, 0)
    item_gap: int = 8
    fab_gap: int = 8
    corner_radius: int = 0
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0
    elevation: float = 0.0

    def copy_with(self, **changes) -> "ToolbarStyle":
        """Return a copy of this style with changed fields."""
        return replace(self, **changes)

    def fab_style(self, size: FabSize = "s") -> FabStyle:
        """Return the style of a FAB placed beside a floating toolbar of this scheme.

        The colour follows :attr:`color_scheme`: secondary-container for
        ``standard``, tertiary-container for ``vibrant``. The elevation is
        level 1 at size ``"s"`` and level 2 otherwise, one level higher while
        hovered.

        Args:
            size: FAB size. MD3 pairs a floating toolbar with ``"s"`` (56dp)
                and ``"m"`` (80dp); ``"l"`` is styled like ``"m"``.

        Returns:
            The derived FAB style.
        """
        base = FabStyle.tertiary(size) if self.color_scheme == "vibrant" else FabStyle.secondary(size)
        elevation = 1 if size == "s" else 2
        return base.copy_with(
            elevation=elevation,
            focused_elevation=elevation,
            hovered_elevation=elevation + 1,
            pressed_elevation=elevation,
        )

    def icon_button_style(self) -> ButtonStyle:
        """Return the style of an icon button hosted by a toolbar of this scheme.

        The container shows the toolbar through; the icon and the state layer
        take :attr:`foreground`.

        Returns:
            The derived icon button style at size ``"s"``.
        """
        return IconButtonStyle.standard().copy_with(
            background=None,
            foreground=self.foreground,
            overlay_color=self.foreground,
        )

    def icon_toggle_button_style(self) -> IconToggleButtonStyle:
        """Return the style pair of an icon toggle button hosted by a toolbar of this scheme.

        Unselected is :meth:`icon_button_style`; selected takes
        :attr:`selected_background` and :attr:`selected_foreground`.

        Returns:
            The derived icon toggle style at size ``"s"``.
        """
        selected = IconToggleButtonStyle.standard().selected.copy_with(
            background=self.selected_background,
            foreground=self.selected_foreground,
            overlay_color=self.selected_foreground,
        )
        return IconToggleButtonStyle(selected=selected, unselected=self.icon_button_style())

    def button_style(self) -> ButtonStyle:
        """Return the style of a text button hosted by a toolbar of this scheme.

        The container shows the toolbar through; the label, icon and state
        layer take :attr:`foreground`.

        Returns:
            The derived button style at size ``"s"``.
        """
        return ButtonStyle.text().copy_with(
            background=None,
            foreground=self.foreground,
            overlay_color=self.foreground,
        )

    def toggle_button_style(self) -> ToggleButtonStyle:
        """Return the style of a text toggle button hosted by a toolbar of this scheme.

        Unselected matches :meth:`button_style`; selected takes
        :attr:`selected_background` and :attr:`selected_foreground`.

        Returns:
            The derived toggle button style at size ``"s"``.
        """
        return ToggleButtonStyle.filled().copy_with(
            unselected_background=None,
            unselected_foreground=self.foreground,
            unselected_overlay_color=self.foreground,
            selected_background=self.selected_background,
            selected_foreground=self.selected_foreground,
            selected_overlay_color=self.selected_foreground,
        )

    @classmethod
    def standard(cls) -> "ToolbarStyle":
        """Return the standard toolbar style."""
        return cls(
            color_scheme="standard",
            background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            foreground=ColorRole.ON_SURFACE_VARIANT,
            selected_background=ColorRole.SECONDARY_CONTAINER,
            selected_foreground=ColorRole.ON_SECONDARY_CONTAINER,
            container_height=64,
            content_insets=(16, 0, 16, 0),
            item_gap=8,
            fab_gap=8,
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
            selected_background=ColorRole.SURFACE_CONTAINER,
            selected_foreground=ColorRole.ON_SURFACE,
            container_height=64,
            content_insets=(16, 0, 16, 0),
            item_gap=8,
            fab_gap=8,
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
