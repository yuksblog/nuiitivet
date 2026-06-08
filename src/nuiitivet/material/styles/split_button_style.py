"""Material Design 3 SplitButton style definitions.

Provides :class:`SplitButtonStyle` with size-specific tokens sourced from the
M3 Expressive split-button component spec:
- https://m3.material.io/components/split-button/specs

Four variant factory methods are available: ``filled``, ``elevated``,
``tonal``, and ``outlined``.  Each accepts a :data:`ButtonSize` token
(``"xs"``–``"xl"``) to select the corresponding M3 size token set.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, TypedDict

from nuiitivet.material.styles.button_size import ButtonSize
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

# ---------------------------------------------------------------------------
# Size token table
# ---------------------------------------------------------------------------


class SplitButtonSizeTokens(TypedDict):
    """Typed view over a single :data:`SPLIT_BUTTON_SIZE_TOKENS` row."""

    container_height: int
    between_space: int
    outer_corner_radius: float
    inner_corner_radius: float
    inner_corner_hovered_radius: float
    inner_corner_pressed_radius: float
    leading_leading_space: int
    leading_trailing_space: int
    trailing_icon_size: int
    trailing_leading_space: int
    trailing_trailing_space: int
    menu_icon_offset: int
    label_font_size: int
    icon_size: int


SPLIT_BUTTON_SIZE_TOKENS: dict[ButtonSize, SplitButtonSizeTokens] = {
    "xs": {
        "container_height": 32,
        "between_space": 2,
        "outer_corner_radius": 16.0,
        "inner_corner_radius": 4.0,
        "inner_corner_hovered_radius": 8.0,
        "inner_corner_pressed_radius": 8.0,
        "leading_leading_space": 12,
        "leading_trailing_space": 10,
        "trailing_icon_size": 22,
        "trailing_leading_space": 13,
        "trailing_trailing_space": 13,
        "menu_icon_offset": -1,
        "label_font_size": 14,
        "icon_size": 20,
    },
    "s": {
        "container_height": 40,
        "between_space": 2,
        "outer_corner_radius": 20.0,
        "inner_corner_radius": 4.0,
        "inner_corner_hovered_radius": 12.0,
        "inner_corner_pressed_radius": 12.0,
        "leading_leading_space": 16,
        "leading_trailing_space": 12,
        "trailing_icon_size": 22,
        "trailing_leading_space": 13,
        "trailing_trailing_space": 13,
        "menu_icon_offset": -1,
        "label_font_size": 14,
        "icon_size": 20,
    },
    "m": {
        "container_height": 56,
        "between_space": 2,
        "outer_corner_radius": 28.0,
        "inner_corner_radius": 4.0,
        "inner_corner_hovered_radius": 12.0,
        "inner_corner_pressed_radius": 12.0,
        "leading_leading_space": 24,
        "leading_trailing_space": 24,
        "trailing_icon_size": 26,
        "trailing_leading_space": 15,
        "trailing_trailing_space": 15,
        "menu_icon_offset": -2,
        "label_font_size": 16,
        "icon_size": 24,
    },
    "l": {
        "container_height": 96,
        "between_space": 2,
        "outer_corner_radius": 48.0,
        "inner_corner_radius": 8.0,
        "inner_corner_hovered_radius": 20.0,
        "inner_corner_pressed_radius": 20.0,
        "leading_leading_space": 48,
        "leading_trailing_space": 48,
        "trailing_icon_size": 38,
        "trailing_leading_space": 29,
        "trailing_trailing_space": 29,
        "menu_icon_offset": -3,
        "label_font_size": 24,
        "icon_size": 32,
    },
    "xl": {
        "container_height": 136,
        "between_space": 2,
        "outer_corner_radius": 68.0,
        "inner_corner_radius": 12.0,
        "inner_corner_hovered_radius": 20.0,
        "inner_corner_pressed_radius": 20.0,
        "leading_leading_space": 64,
        "leading_trailing_space": 64,
        "trailing_icon_size": 50,
        "trailing_leading_space": 43,
        "trailing_trailing_space": 43,
        "menu_icon_offset": -6,
        "label_font_size": 32,
        "icon_size": 40,
    },
}


# ---------------------------------------------------------------------------
# SplitButtonStyle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SplitButtonStyle:
    """Immutable style for :class:`SplitButton` (M3 Expressive-compliant).

    Use the ``filled``, ``elevated``, ``tonal``, or ``outlined`` factory
    classmethods rather than constructing directly where possible.

    All size-related tokens are driven by :data:`SPLIT_BUTTON_SIZE_TOKENS`.
    """

    # Container colours
    background: Optional[ColorSpec] = None
    foreground: Optional[ColorSpec] = None
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0

    # Elevation
    elevation: int = 0

    # State overlay
    overlay_color: Optional[ColorSpec] = None
    overlay_alpha: float = 0.12

    # Size tokens (derived from SPLIT_BUTTON_SIZE_TOKENS)
    container_height: int = 40
    between_space: int = 2
    outer_corner_radius: float = 20.0
    inner_corner_radius: float = 4.0
    inner_corner_hovered_radius: float = 12.0
    inner_corner_pressed_radius: float = 12.0
    leading_leading_space: int = 16
    leading_trailing_space: int = 12
    trailing_icon_size: int = 22
    trailing_leading_space: int = 13
    trailing_trailing_space: int = 13
    menu_icon_offset: int = -1
    label_font_size: int = 14
    icon_size: int = 20

    def copy_with(self, **changes) -> "SplitButtonStyle":
        """Return a new style with the specified fields replaced.

        Args:
            **changes: Fields to override.

        Returns:
            A new :class:`SplitButtonStyle` instance.
        """
        return replace(self, **changes)

    @classmethod
    def filled(cls, size: ButtonSize = "s") -> "SplitButtonStyle":
        """Create a filled-variant style.

        Uses ``Primary`` as the container colour.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).

        Returns:
            A new :class:`SplitButtonStyle` instance.
        """
        t = SPLIT_BUTTON_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            border_width=0.0,
            overlay_color=ColorRole.ON_PRIMARY,
            overlay_alpha=0.12,
            **t,
        )

    @classmethod
    def elevated(cls, size: ButtonSize = "s") -> "SplitButtonStyle":
        """Create an elevated-variant style.

        Uses ``Surface`` as the container colour with elevation level 1.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).

        Returns:
            A new :class:`SplitButtonStyle` instance.
        """
        t = SPLIT_BUTTON_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SURFACE_CONTAINER_LOW,
            foreground=ColorRole.PRIMARY,
            border_width=0.0,
            elevation=1,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.08,
            **t,
        )

    @classmethod
    def tonal(cls, size: ButtonSize = "s") -> "SplitButtonStyle":
        """Create a tonal-variant style.

        Uses ``SecondaryContainer`` as the container colour.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).

        Returns:
            A new :class:`SplitButtonStyle` instance.
        """
        t = SPLIT_BUTTON_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SECONDARY_CONTAINER,
            foreground=ColorRole.ON_SECONDARY_CONTAINER,
            border_width=0.0,
            overlay_color=ColorRole.ON_SECONDARY_CONTAINER,
            overlay_alpha=0.12,
            **t,
        )

    @classmethod
    def outlined(cls, size: ButtonSize = "s") -> "SplitButtonStyle":
        """Create an outlined-variant style.

        Uses a transparent background with an ``Outline``-coloured border.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).

        Returns:
            A new :class:`SplitButtonStyle` instance.
        """
        t = SPLIT_BUTTON_SIZE_TOKENS[size]
        return cls(
            background=None,
            foreground=ColorRole.ON_SURFACE,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.08,
            **t,
        )


__all__ = [
    "SplitButtonSizeTokens",
    "SPLIT_BUTTON_SIZE_TOKENS",
    "SplitButtonStyle",
]
