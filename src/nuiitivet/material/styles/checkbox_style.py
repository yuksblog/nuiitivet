"""Checkbox widget style.

Provides the concrete `CheckboxStyle` implementation previously defined
under `nuiitivet.ui.styles.checkbox` and adjusted to the flat package
layout under `nuiitivet.material.styles.checkbox`.
"""

from dataclasses import dataclass, replace

from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.types import ColorSpec

from ..theme.color_role import ColorRole

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


@dataclass(frozen=True)
class CheckboxStyle:
    """Immutable style for Checkbox widgets (M3準拠).

    Material Design 3 Checkbox specifications:
    - Touch target: 48x48 dp
    - Icon size: 18 dp (37.5% of touch target)
    - State layer: 40 dp diameter (83.3% of touch target)
    - Corner radius: 2 dp (11.1% of icon size)
    - Stroke width: 2 dp (11.1% of icon size)
    """

    # Size properties (M3 baseline: 48dp touch target)
    default_touch_target: int = 48
    padding: int = 0
    icon_size_ratio: float = 18.0 / 48.0  # Icon size relative to touch target
    corner_radius_ratio: float = 0.111  # Corner radius relative to icon size
    stroke_width_ratio: float = 0.11  # Stroke width relative to icon size

    # Colors
    stroke_color: ColorSpec = ColorRole.ON_SURFACE
    stroke_alpha: float = 0.54  # Medium emphasis per M3
    checked_background: ColorSpec = ColorRole.PRIMARY
    checked_foreground: ColorSpec = ColorRole.ON_PRIMARY

    # Disabled colors (M3: outline and container are on-surface @ 38%, mark is surface)
    disabled_color: ColorSpec = ColorRole.ON_SURFACE
    disabled_mark: ColorSpec = ColorRole.SURFACE
    disabled_alpha: float = 0.38

    # State layer (hover/press overlay)
    state_layer_ratio: float = 40.0 / 48.0  # State layer diameter relative to touch target
    hover_alpha: float = 0.08
    pressed_alpha: float = 0.12

    def copy_with(self, **changes) -> "CheckboxStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict:
        """Resolve role colors to concrete RGBA values."""

        return {
            "stroke_color": resolve_color_to_rgba(self.stroke_color, theme=theme),
            "checked_background": resolve_color_to_rgba(self.checked_background, theme=theme),
            "checked_foreground": resolve_color_to_rgba(self.checked_foreground, theme=theme),
            "disabled_color": resolve_color_to_rgba(self.disabled_color, theme=theme),
            "disabled_mark": resolve_color_to_rgba(self.disabled_mark, theme=theme),
        }

    def compute_sizes(self, touch_target_size: int) -> dict:
        """Compute pixel sizes based on touch target size."""
        icon_sz = int(max(12, round(touch_target_size * self.icon_size_ratio)))
        corner = max(1.0, float(icon_sz) * self.corner_radius_ratio)
        stroke_w = max(1.0, float(icon_sz) * self.stroke_width_ratio)
        state_diam = touch_target_size * self.state_layer_ratio

        return {
            "icon_size": icon_sz,
            "corner_radius": corner,
            "stroke_width": stroke_w,
            "state_layer_diameter": state_diam,
            "state_layer_size": state_diam,
        }


__all__ = ["CheckboxStyle"]
