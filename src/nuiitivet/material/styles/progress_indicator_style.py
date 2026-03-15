"""Progress indicator style definitions (Material Design 3)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, TypeVar

from nuiitivet.animation.motion import Motion
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme import Theme


TProgressStyle = TypeVar("TProgressStyle", bound="ProgressIndicatorStyle")


@dataclass(frozen=True)
class ProgressIndicatorStyle:
    """Shared style tokens for progress indicators."""

    active_indicator_color: ColorSpec = ColorRole.PRIMARY
    track_color: ColorSpec = ColorRole.SECONDARY_CONTAINER
    stop_indicator_color: ColorSpec = ColorRole.PRIMARY

    disabled_active_alpha: float = 0.38
    disabled_track_alpha: float = 0.12

    def copy_with(self: TProgressStyle, **changes: Any) -> TProgressStyle:
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True)
class LinearProgressIndicatorStyle(ProgressIndicatorStyle):
    """Linear progress indicator geometry and motion tokens."""

    track_thickness: float = 4.0
    with_wave_height: float = 10.0
    stop_indicator_size: float = 4.0
    track_active_space: float = 4.0
    stop_indicator_trailing_space: float = 0.0

    wave_amplitude: float = 3.0
    wave_wavelength: float = 40.0
    indeterminate_wave_wavelength: float = 20.0

    motion: Motion = EXPRESSIVE_DEFAULT_EFFECTS

    @classmethod
    def default(cls) -> "LinearProgressIndicatorStyle":
        """Create the default linear progress style."""
        return cls()

    @classmethod
    def flat(cls) -> "LinearProgressIndicatorStyle":
        """Create a flat linear progress style preset."""
        return cls(
            with_wave_height=4.0,
            wave_amplitude=0.0,
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "default") -> "LinearProgressIndicatorStyle":
        """Get linear progress style from theme.

        Args:
            theme: Theme to load style from.
            variant: Variant name ("default" or "flat").

        Returns:
            LinearProgressIndicatorStyle resolved from theme or fallback preset.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        v = (variant or "").lower()

        if theme_data is not None:
            base = theme_data.linear_progress_indicator_style
            if v == "flat":
                return base.copy_with(with_wave_height=base.track_thickness, wave_amplitude=0.0)
            return base

        if v == "flat":
            return cls.flat()
        return cls.default()


@dataclass(frozen=True)
class CircularProgressIndicatorStyle(ProgressIndicatorStyle):
    """Circular progress indicator geometry and motion tokens."""

    size: float = 40.0
    with_wave_size: float = 48.0
    track_thickness: float = 4.0
    track_active_space: float = 4.0

    wave_amplitude: float = 1.6
    wave_wavelength: float = 15.0

    motion: Motion = EXPRESSIVE_DEFAULT_EFFECTS

    @classmethod
    def default(cls) -> "CircularProgressIndicatorStyle":
        """Create the default circular progress style."""
        return cls()

    @classmethod
    def flat(cls) -> "CircularProgressIndicatorStyle":
        """Create a flat circular progress style preset."""
        return cls(
            with_wave_size=40.0,
            wave_amplitude=0.0,
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "default") -> "CircularProgressIndicatorStyle":
        """Get circular progress style from theme.

        Args:
            theme: Theme to load style from.
            variant: Variant name ("default" or "flat").

        Returns:
            CircularProgressIndicatorStyle resolved from theme or fallback preset.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        v = (variant or "").lower()

        if theme_data is not None:
            base = theme_data.circular_progress_indicator_style
            if v == "flat":
                return base.copy_with(with_wave_size=base.size, wave_amplitude=0.0)
            return base

        if v == "flat":
            return cls.flat()
        return cls.default()


__all__ = [
    "ProgressIndicatorStyle",
    "LinearProgressIndicatorStyle",
    "CircularProgressIndicatorStyle",
]
