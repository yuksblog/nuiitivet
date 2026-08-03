"""Menu widget style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


@dataclass(frozen=True)
class MenuStyle:
    """Immutable style for Material Design 3 Vertical Menu widgets."""

    background: ColorSpec = ColorRole.SURFACE
    corner_radius: int = 16
    min_width: int = 112
    max_width: int = 280
    container_vertical_padding: int = 8

    item_height: int = 44
    item_horizontal_inset: int = 4
    item_horizontal_padding: int = 12
    item_spacing: int = 12
    icon_size: int = 20
    label_color: ColorSpec = ColorRole.ON_SURFACE
    icon_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    trailing_text_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    disabled_color: ColorSpec = ColorRole.ON_SURFACE

    state_layer_color: ColorSpec = ColorRole.ON_SURFACE
    hover_alpha: float = 0.08
    focus_alpha: float = 0.1
    pressed_alpha: float = 0.1
    state_layer_corner_radius: int = 8
    disabled_opacity: float = 0.38
    selected_disabled_background_opacity: float | None = 0.38
    interactive_icon_color: ColorSpec | None = None

    elevation: int = 2  # MD3 elevation level (0–5); menu = level 2 = 3 dp

    selected_background: ColorSpec = ColorRole.TERTIARY_CONTAINER
    selected_foreground: ColorSpec = ColorRole.ON_TERTIARY_CONTAINER

    divider_color: ColorSpec = ColorRole.OUTLINE_VARIANT
    divider_vertical_padding: int = 8

    def copy_with(self, **changes) -> "MenuStyle":
        """Return a copy of this style with selected fields overridden."""
        return replace(self, **changes)

    @classmethod
    def standard(cls) -> "MenuStyle":
        """Return the standard (surface-based) menu style."""
        return cls()

    @classmethod
    def vibrant(cls) -> "MenuStyle":
        """Return the vibrant (tertiary-based) menu style."""
        return cls(
            background=ColorRole.TERTIARY_CONTAINER,
            label_color=ColorRole.ON_TERTIARY_CONTAINER,
            icon_color=ColorRole.ON_TERTIARY_CONTAINER,
            trailing_text_color=ColorRole.ON_TERTIARY_CONTAINER,
            state_layer_color=ColorRole.ON_TERTIARY_CONTAINER,
            selected_background=ColorRole.TERTIARY,
            selected_foreground=ColorRole.ON_TERTIARY,
            selected_disabled_background_opacity=None,
            interactive_icon_color=ColorRole.TERTIARY,
        )

    @classmethod
    def preset(cls, variant: str = "standard") -> "MenuStyle":
        """Return the framework preset for ``variant``, ignoring any theme.

        This is what a menu renders with before it is mounted, and what
        :meth:`from_theme` falls back to when no Material theme is installed.

        Args:
            variant: One of ``"standard"`` or ``"vibrant"``. Unknown values
                fall back to ``"standard"``.

        Returns:
            The variant preset style.
        """
        if str(variant or "standard").lower() == "vibrant":
            return cls.vibrant()
        return cls.standard()

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "standard") -> "MenuStyle":
        """Resolve MenuStyle from theme.

        Args:
            theme: Theme instance.
            variant: One of ``"standard"`` or ``"vibrant"``. Only ``standard``
                is carried by :class:`MaterialThemeData`; ``vibrant`` is an
                explicit opt-in and always returns its preset.

        Returns:
            Resolved ``MenuStyle``.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        variant_name = str(variant or "standard").lower()
        if variant_name == "standard":
            theme_data = theme.extension(MaterialThemeData)
            if theme_data is not None:
                return theme_data.menu_style
        return cls.preset(variant_name)


__all__ = ["MenuStyle"]
