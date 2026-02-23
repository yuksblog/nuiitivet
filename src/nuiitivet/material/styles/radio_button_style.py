"""RadioButton widget style."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.types import ColorSpec

from ..theme.color_role import ColorRole

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


@dataclass(frozen=True)
class RadioButtonStyle:
    """Immutable style for RadioButton widgets.

    Material Design 3 RadioButton baseline:
    - Touch target: 48x48 dp
    - Icon diameter: 20 dp
    - Inner dot diameter: 10 dp
    """

    default_touch_target: int = 48
    padding: int = 0

    icon_diameter_ratio: float = 20.0 / 48.0
    inner_dot_ratio: float = 10.0 / 20.0
    stroke_width_ratio: float = 2.0 / 20.0

    unselected_stroke: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    selected_stroke: ColorSpec = ColorRole.PRIMARY
    selected_dot: ColorSpec = ColorRole.PRIMARY
    disabled_stroke: ColorSpec = ColorRole.ON_SURFACE
    disabled_alpha: float = 0.38

    state_layer_ratio: float = 40.0 / 48.0
    hover_alpha: float = 0.08
    pressed_alpha: float = 0.12

    focus_stroke_ratio: float = 3.0 / 48.0
    focus_offset_ratio: float = 2.0 / 48.0
    focus_alpha: float = 0.12
    focus_color: ColorSpec = ColorRole.PRIMARY

    def copy_with(self, **changes) -> "RadioButtonStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict[str, tuple[int, int, int, int] | None]:
        """Resolve role colors to concrete RGBA values."""
        return {
            "unselected_stroke": resolve_color_to_rgba(self.unselected_stroke, theme=theme),
            "selected_stroke": resolve_color_to_rgba(self.selected_stroke, theme=theme),
            "selected_dot": resolve_color_to_rgba(self.selected_dot, theme=theme),
            "disabled_stroke": resolve_color_to_rgba(self.disabled_stroke, theme=theme),
            "focus_color": resolve_color_to_rgba(self.focus_color, theme=theme),
        }

    def compute_sizes(self, touch_target_size: int) -> dict[str, float | int]:
        """Compute pixel sizes based on touch target size."""
        icon_diameter = int(max(14, round(touch_target_size * self.icon_diameter_ratio)))
        inner_dot = max(4.0, float(icon_diameter) * self.inner_dot_ratio)
        stroke_width = max(1.0, float(icon_diameter) * self.stroke_width_ratio)
        state_layer_size = float(touch_target_size) * self.state_layer_ratio
        focus_stroke = max(1.0, float(touch_target_size) * self.focus_stroke_ratio)
        focus_offset = float(touch_target_size) * self.focus_offset_ratio

        return {
            "icon_diameter": icon_diameter,
            "inner_dot": inner_dot,
            "stroke_width": stroke_width,
            "state_layer_size": state_layer_size,
            "focus_stroke": focus_stroke,
            "focus_offset": focus_offset,
        }


__all__ = ["RadioButtonStyle"]
