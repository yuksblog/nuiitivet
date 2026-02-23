"""Switch widget style."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.types import ColorSpec

from ..theme.color_role import ColorRole

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


@dataclass(frozen=True)
class SwitchStyle:
    """Immutable style for Switch widgets."""

    default_touch_target: int = 48
    padding: int = 0

    track_width_ratio: float = 52.0 / 48.0
    track_height_ratio: float = 32.0 / 48.0
    thumb_diameter_ratio: float = 20.0 / 48.0

    checked_track: ColorSpec = ColorRole.PRIMARY
    unchecked_track: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGHEST
    checked_thumb: ColorSpec = ColorRole.ON_PRIMARY
    unchecked_thumb: ColorSpec = ColorRole.OUTLINE
    disabled_track: ColorSpec = ColorRole.ON_SURFACE
    disabled_thumb: ColorSpec = ColorRole.SURFACE
    disabled_alpha: float = 0.38

    state_layer_ratio: float = 40.0 / 48.0
    hover_alpha: float = 0.08
    pressed_alpha: float = 0.12

    focus_stroke_ratio: float = 3.0 / 48.0
    focus_offset_ratio: float = 2.0 / 48.0
    focus_alpha: float = 0.12
    focus_color: ColorSpec = ColorRole.PRIMARY

    def copy_with(self, **changes) -> "SwitchStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict[str, tuple[int, int, int, int] | None]:
        """Resolve role colors to concrete RGBA values."""
        return {
            "checked_track": resolve_color_to_rgba(self.checked_track, theme=theme),
            "unchecked_track": resolve_color_to_rgba(self.unchecked_track, theme=theme),
            "checked_thumb": resolve_color_to_rgba(self.checked_thumb, theme=theme),
            "unchecked_thumb": resolve_color_to_rgba(self.unchecked_thumb, theme=theme),
            "disabled_track": resolve_color_to_rgba(self.disabled_track, theme=theme),
            "disabled_thumb": resolve_color_to_rgba(self.disabled_thumb, theme=theme),
            "focus_color": resolve_color_to_rgba(self.focus_color, theme=theme),
        }

    def compute_sizes(self, touch_target_size: int) -> dict[str, float | int]:
        """Compute pixel sizes based on touch target size."""
        track_width = max(36.0, float(touch_target_size) * self.track_width_ratio)
        track_height = max(24.0, float(touch_target_size) * self.track_height_ratio)
        thumb_diameter = max(12.0, float(touch_target_size) * self.thumb_diameter_ratio)
        state_layer_size = float(touch_target_size) * self.state_layer_ratio
        focus_stroke = max(1.0, float(touch_target_size) * self.focus_stroke_ratio)
        focus_offset = float(touch_target_size) * self.focus_offset_ratio

        return {
            "track_width": track_width,
            "track_height": track_height,
            "thumb_diameter": thumb_diameter,
            "state_layer_size": state_layer_size,
            "focus_stroke": focus_stroke,
            "focus_offset": focus_offset,
        }


__all__ = ["SwitchStyle"]
