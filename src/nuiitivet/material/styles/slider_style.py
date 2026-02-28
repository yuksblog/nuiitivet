"""Slider widget style definitions (MD3 Expressive)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class SliderStyle:
    """Immutable style for Slider widgets (MD3 Expressive)."""

    active_track_height: float = 16.0
    active_track_leading_shape: float = 8.0
    inactive_track_height: float = 16.0
    inactive_track_trailing_shape: float = 8.0

    active_handle_height: float = 44.0
    handle_width: float = 4.0
    handle_width_focused: float = 2.0
    handle_leading_space: float = 6.0
    handle_trailing_space: float = 6.0

    stop_indicator_size: float = 4.0
    stop_indicator_trailing_space: float = 6.0

    value_indicator_height: float = 44.0
    value_indicator_width: float = 48.0
    value_indicator_bottom_space: float = 12.0

    state_layer_size: float = 40.0

    active_track_color: ColorSpec = ColorRole.PRIMARY
    inactive_track_color: ColorSpec = ColorRole.SECONDARY_CONTAINER
    handle_color: ColorSpec = ColorRole.PRIMARY
    active_stop_indicator_color: ColorSpec = ColorRole.ON_PRIMARY
    inactive_stop_indicator_color: ColorSpec = ColorRole.ON_SECONDARY_CONTAINER
    value_indicator_color: ColorSpec = ColorRole.SURFACE
    value_indicator_text_color: ColorSpec = ColorRole.ON_SURFACE

    disabled_active_track_color: ColorSpec = ColorRole.ON_SURFACE
    disabled_active_track_alpha: float = 0.38
    disabled_inactive_track_color: ColorSpec = ColorRole.ON_SURFACE
    disabled_inactive_track_alpha: float = 0.12
    disabled_handle_color: ColorSpec = ColorRole.ON_SURFACE
    disabled_handle_alpha: float = 0.38

    focus_stroke_ratio: float = 3.0 / 48.0
    focus_offset_ratio: float = 2.0 / 48.0
    focus_alpha: float = 0.12
    focus_color: ColorSpec = ColorRole.PRIMARY

    def copy_with(self, **changes) -> "SliderStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    @classmethod
    def xs(cls) -> "SliderStyle":
        """Create XS slider style preset."""
        return cls(
            active_track_height=16.0,
            active_track_leading_shape=8.0,
            inactive_track_height=16.0,
            inactive_track_trailing_shape=8.0,
            active_handle_height=44.0,
        )

    @classmethod
    def s(cls) -> "SliderStyle":
        """Create S slider style preset."""
        return cls(
            active_track_height=24.0,
            active_track_leading_shape=8.0,
            inactive_track_height=24.0,
            inactive_track_trailing_shape=8.0,
            active_handle_height=44.0,
        )

    @classmethod
    def m(cls) -> "SliderStyle":
        """Create M slider style preset."""
        return cls(
            active_track_height=40.0,
            active_track_leading_shape=12.0,
            inactive_track_height=40.0,
            inactive_track_trailing_shape=12.0,
            active_handle_height=52.0,
        )

    @classmethod
    def l(cls) -> "SliderStyle":  # noqa: E743
        """Create L slider style preset."""
        return cls(
            active_track_height=56.0,
            active_track_leading_shape=16.0,
            inactive_track_height=56.0,
            inactive_track_trailing_shape=16.0,
            active_handle_height=68.0,
        )

    @classmethod
    def xl(cls) -> "SliderStyle":
        """Create XL slider style preset."""
        return cls(
            active_track_height=96.0,
            active_track_leading_shape=28.0,
            inactive_track_height=96.0,
            inactive_track_trailing_shape=28.0,
            active_handle_height=108.0,
        )


__all__ = ["SliderStyle"]
