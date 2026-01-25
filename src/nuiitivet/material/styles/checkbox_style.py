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

    # State layer (hover/press overlay)
    state_layer_ratio: float = 40.0 / 48.0  # State layer diameter relative to touch target
    hover_alpha: float = 0.08
    pressed_alpha: float = 0.12

    # Focus indicator (M3 spec: 3dp stroke, 2dp offset at 48dp touch target)
    focus_stroke_ratio: float = 3.0 / 48.0  # Focus stroke relative to touch target
    focus_offset_ratio: float = 2.0 / 48.0  # Focus offset relative to touch target
    focus_alpha: float = 0.12
    focus_color: ColorSpec = ColorRole.PRIMARY

    def copy_with(self, **changes) -> "CheckboxStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict:
        """Resolve role colors to concrete RGBA values."""

        return {
            "stroke_color": resolve_color_to_rgba(self.stroke_color, theme=theme),
            "checked_background": resolve_color_to_rgba(self.checked_background, theme=theme),
            "checked_foreground": resolve_color_to_rgba(self.checked_foreground, theme=theme),
            "focus_color": resolve_color_to_rgba(self.focus_color, theme=theme),
        }

    def compute_sizes(self, touch_target_size: int) -> dict:
        """Compute pixel sizes based on touch target size."""
        icon_sz = int(max(12, round(touch_target_size * self.icon_size_ratio)))
        corner = max(1.0, float(icon_sz) * self.corner_radius_ratio)
        stroke_w = max(1.0, float(icon_sz) * self.stroke_width_ratio)
        state_diam = touch_target_size * self.state_layer_ratio
        focus_stroke = max(1.0, float(touch_target_size) * self.focus_stroke_ratio)
        focus_offset = float(touch_target_size) * self.focus_offset_ratio

        return {
            "icon_size": icon_sz,
            "corner_radius": corner,
            "stroke_width": stroke_w,
            "state_layer_diameter": state_diam,
            "state_layer_size": state_diam,
            "focus_stroke": focus_stroke,
            "focus_offset": focus_offset,
        }


__all__ = ["CheckboxStyle"]
