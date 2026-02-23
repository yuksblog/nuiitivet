"""Chip widget style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


@dataclass(frozen=True)
class ChipStyle:
    """Immutable style for Material Design 3 chip widgets.

    Args:
        background: Container background color.
        foreground: Label and icon color.
        border_color: Border color.
        border_width: Border width in pixels.
        corner_radius: Container corner radius in pixels.
        container_height: Visual container height in pixels.
        padding: Content insets (left, top, right, bottom).
        spacing: Gap between chip content items.
        min_width: Minimum chip width.
        min_height: Minimum touch target height.
        state_layer_color: Overlay color for hover/press/drag states.
        hover_alpha: State layer opacity for hover.
        pressed_alpha: State layer opacity for pressed.
        drag_alpha: State layer opacity for drag.
        selected_background: Container background when selected (filter chip).
        selected_foreground: Foreground color when selected (filter chip).
        selected_border_color: Border color when selected (filter chip).
    """

    background: ColorSpec = ColorRole.SURFACE
    foreground: ColorSpec = ColorRole.ON_SURFACE
    border_color: ColorSpec = ColorRole.OUTLINE
    border_width: float = 1.0
    corner_radius: int = 8

    container_height: int = 32
    padding: tuple[int, int, int, int] = (8, 0, 8, 0)
    spacing: int = 8
    min_width: int = 48
    min_height: int = 48

    state_layer_color: ColorSpec = ColorRole.ON_SURFACE
    hover_alpha: float = 0.08
    pressed_alpha: float = 0.12
    drag_alpha: float = 0.16

    selected_background: ColorSpec | None = ColorRole.SECONDARY_CONTAINER
    selected_foreground: ColorSpec | None = ColorRole.ON_SECONDARY_CONTAINER
    selected_border_color: ColorSpec | None = ColorRole.SECONDARY_CONTAINER

    def copy_with(self, **changes) -> "ChipStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    @classmethod
    def assist(cls) -> "ChipStyle":
        """Create default assist chip style."""
        return cls(
            background=ColorRole.SURFACE,
            foreground=ColorRole.ON_SURFACE,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            state_layer_color=ColorRole.ON_SURFACE,
        )

    @classmethod
    def filter(cls) -> "ChipStyle":
        """Create default filter chip style."""
        return cls(
            background=ColorRole.SURFACE,
            foreground=ColorRole.ON_SURFACE,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            state_layer_color=ColorRole.ON_SURFACE,
            selected_background=ColorRole.SECONDARY_CONTAINER,
            selected_foreground=ColorRole.ON_SECONDARY_CONTAINER,
            selected_border_color=ColorRole.SECONDARY_CONTAINER,
        )

    @classmethod
    def input(cls) -> "ChipStyle":
        """Create default input chip style."""
        return cls(
            background=ColorRole.SURFACE,
            foreground=ColorRole.ON_SURFACE,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            state_layer_color=ColorRole.ON_SURFACE,
        )

    @classmethod
    def suggestion(cls) -> "ChipStyle":
        """Create default suggestion chip style."""
        return cls(
            background=ColorRole.SURFACE,
            foreground=ColorRole.ON_SURFACE,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            state_layer_color=ColorRole.ON_SURFACE,
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str) -> "ChipStyle":
        """Resolve chip style from theme for the given variant.

        Args:
            theme: Theme instance.
            variant: One of ``assist``, ``filter``, ``input``, ``suggestion``.

        Returns:
            Resolved chip style.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        variant_name = (variant or "assist").lower()

        if theme_data is not None:
            if variant_name == "assist":
                return theme_data.assist_chip_style
            if variant_name == "filter":
                return theme_data.filter_chip_style
            if variant_name == "input":
                return theme_data.input_chip_style
            if variant_name == "suggestion":
                return theme_data.suggestion_chip_style

        if variant_name == "assist":
            return cls.assist()
        if variant_name == "filter":
            return cls.filter()
        if variant_name == "input":
            return cls.input()
        if variant_name == "suggestion":
            return cls.suggestion()
        return cls.assist()


__all__ = ["ChipStyle"]
