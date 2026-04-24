"""ToggleButtonStyle definition for M3 toggle buttons.

Models selected/unselected visual states explicitly, matching the M3
"Button - Color - <variant>" toggle rows:
https://m3.material.io/components/buttons/specs

Available size-aware factories: :meth:`ToggleButtonStyle.filled`,
:meth:`ToggleButtonStyle.outlined`, :meth:`ToggleButtonStyle.elevated`,
:meth:`ToggleButtonStyle.tonal`.  A ``text`` variant is intentionally not
provided because the MD3 spec does not define toggle states for the text
variant.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from .button_size import BUTTON_SIZE_TOKENS, ButtonSize
from .button_style import ButtonStyle, PaddingLike, _size_min_height, _size_min_width, _size_padding
from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class ToggleButtonStyle:
    """Immutable style for :class:`ToggleButton` (M3-compliant).

    Stores a single flat set of shape/size tokens plus two paired colour
    groups: ``unselected_*`` and ``selected_*``.  The :meth:`for_selected`
    helper projects the style into a :class:`ButtonStyle` for the active
    state, so the widget internals can reuse the normal Button machinery.
    """

    # Shape / size (shared across states)
    container_height: int = 40
    corner_radius: int = 20
    padding: PaddingLike = (16, 0, 16, 0)
    spacing: int = 8
    min_width: int = 64
    min_height: int = 48
    label_font_size: int = 14
    icon_size: int = 20
    border_width: float = 0.0
    elevation: float = 0.0

    # Unselected-state colours
    unselected_background: Optional[ColorSpec] = None
    unselected_foreground: Optional[ColorSpec] = None
    unselected_border_color: Optional[ColorSpec] = None
    unselected_overlay_color: Optional[ColorSpec] = None
    unselected_overlay_alpha: float = 0.08

    # Selected-state colours
    selected_background: Optional[ColorSpec] = None
    selected_foreground: Optional[ColorSpec] = None
    selected_border_color: Optional[ColorSpec] = None
    selected_overlay_color: Optional[ColorSpec] = None
    selected_overlay_alpha: float = 0.08

    def copy_with(self, **changes) -> "ToggleButtonStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def for_selected(self, selected: bool) -> ButtonStyle:
        """Project this style into a :class:`ButtonStyle` for the given state.

        Args:
            selected: When ``True``, project the selected-state colours;
                otherwise use unselected-state colours.
        """
        if selected:
            return ButtonStyle(
                background=self.selected_background,
                foreground=self.selected_foreground,
                border_color=self.selected_border_color,
                border_width=self.border_width,
                corner_radius=self.corner_radius,
                container_height=self.container_height,
                padding=self.padding,
                spacing=self.spacing,
                min_width=self.min_width,
                min_height=self.min_height,
                label_font_size=self.label_font_size,
                icon_size=self.icon_size,
                elevation=self.elevation,
                overlay_color=self.selected_overlay_color,
                overlay_alpha=self.selected_overlay_alpha,
            )
        return ButtonStyle(
            background=self.unselected_background,
            foreground=self.unselected_foreground,
            border_color=self.unselected_border_color,
            border_width=self.border_width,
            corner_radius=self.corner_radius,
            container_height=self.container_height,
            padding=self.padding,
            spacing=self.spacing,
            min_width=self.min_width,
            min_height=self.min_height,
            label_font_size=self.label_font_size,
            icon_size=self.icon_size,
            elevation=self.elevation,
            overlay_color=self.unselected_overlay_color,
            overlay_alpha=self.unselected_overlay_alpha,
        )

    # -- Factory classmethods (size-aware) ----------------------------------

    @classmethod
    def filled(cls, size: ButtonSize = "s") -> "ToggleButtonStyle":
        """Return the filled toggle-button style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            container_height=t["container_height"],
            corner_radius=t["corner_radius"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            border_width=0.0,
            elevation=0.0,
            unselected_background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            unselected_foreground=ColorRole.ON_SURFACE_VARIANT,
            unselected_border_color=None,
            unselected_overlay_color=ColorRole.ON_SURFACE_VARIANT,
            unselected_overlay_alpha=0.08,
            selected_background=ColorRole.PRIMARY,
            selected_foreground=ColorRole.ON_PRIMARY,
            selected_border_color=None,
            selected_overlay_color=ColorRole.ON_PRIMARY,
            selected_overlay_alpha=0.08,
        )

    @classmethod
    def outlined(cls, size: ButtonSize = "s") -> "ToggleButtonStyle":
        """Return the outlined toggle-button style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            container_height=t["container_height"],
            corner_radius=t["corner_radius"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            border_width=t["outline_width"],
            elevation=0.0,
            unselected_background=None,
            unselected_foreground=ColorRole.ON_SURFACE_VARIANT,
            unselected_border_color=ColorRole.OUTLINE_VARIANT,
            unselected_overlay_color=ColorRole.ON_SURFACE_VARIANT,
            unselected_overlay_alpha=0.08,
            selected_background=ColorRole.INVERSE_SURFACE,
            selected_foreground=ColorRole.INVERSE_ON_SURFACE,
            selected_border_color=ColorRole.INVERSE_SURFACE,
            selected_overlay_color=ColorRole.INVERSE_ON_SURFACE,
            selected_overlay_alpha=0.08,
        )

    @classmethod
    def elevated(cls, size: ButtonSize = "s") -> "ToggleButtonStyle":
        """Return the elevated toggle-button style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            container_height=t["container_height"],
            corner_radius=t["corner_radius"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            border_width=0.0,
            elevation=1.0,
            unselected_background=ColorRole.SURFACE_CONTAINER_LOW,
            unselected_foreground=ColorRole.PRIMARY,
            unselected_border_color=None,
            unselected_overlay_color=ColorRole.PRIMARY,
            unselected_overlay_alpha=0.08,
            selected_background=ColorRole.PRIMARY,
            selected_foreground=ColorRole.ON_PRIMARY,
            selected_border_color=None,
            selected_overlay_color=ColorRole.ON_PRIMARY,
            selected_overlay_alpha=0.08,
        )

    @classmethod
    def tonal(cls, size: ButtonSize = "s") -> "ToggleButtonStyle":
        """Return the tonal toggle-button style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            container_height=t["container_height"],
            corner_radius=t["corner_radius"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            border_width=0.0,
            elevation=0.0,
            unselected_background=ColorRole.SECONDARY_CONTAINER,
            unselected_foreground=ColorRole.ON_SECONDARY_CONTAINER,
            unselected_border_color=None,
            unselected_overlay_color=ColorRole.ON_SECONDARY_CONTAINER,
            unselected_overlay_alpha=0.08,
            selected_background=ColorRole.SECONDARY,
            selected_foreground=ColorRole.ON_SECONDARY,
            selected_border_color=None,
            selected_overlay_color=ColorRole.ON_SECONDARY,
            selected_overlay_alpha=0.08,
        )


__all__ = ["ToggleButtonStyle"]
