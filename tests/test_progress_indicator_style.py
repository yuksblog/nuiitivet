"""Tests for progress indicator styles and theme integration."""

from dataclasses import replace

from nuiitivet.material.styles import (
    CircularProgressIndicatorStyle,
    LinearProgressIndicatorStyle,
    ProgressIndicatorStyle,
)
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.theme_data import MaterialThemeData


def test_progress_indicator_style_defaults():
    style = ProgressIndicatorStyle()
    assert style.active_indicator_color == ColorRole.PRIMARY
    assert style.track_color == ColorRole.SECONDARY_CONTAINER
    assert style.stop_indicator_color == ColorRole.PRIMARY
    assert style.disabled_active_alpha == 0.38
    assert style.disabled_track_alpha == 0.12


def test_linear_progress_style_presets():
    default = LinearProgressIndicatorStyle.default()
    flat = LinearProgressIndicatorStyle.flat()

    assert default.track_thickness == 4.0
    assert default.with_wave_height == 10.0
    assert default.wave_amplitude == 3.0

    assert flat.track_thickness == 4.0
    assert flat.with_wave_height == 4.0
    assert flat.wave_amplitude == 0.0


def test_circular_progress_style_presets():
    default = CircularProgressIndicatorStyle.default()
    flat = CircularProgressIndicatorStyle.flat()

    assert default.size == 40.0
    assert default.with_wave_size == 48.0
    assert default.wave_amplitude == 1.6

    assert flat.size == 40.0
    assert flat.with_wave_size == 40.0
    assert flat.wave_amplitude == 0.0


def test_progress_style_copy_with():
    base = LinearProgressIndicatorStyle.default()
    custom = base.copy_with(active_indicator_color=ColorRole.TERTIARY, track_thickness=6.0)

    assert custom.active_indicator_color == ColorRole.TERTIARY
    assert custom.track_thickness == 6.0
    assert custom.with_wave_height == base.with_wave_height


def test_theme_with_custom_progress_styles():
    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    mat = light.extension(MaterialThemeData)
    assert mat is not None

    custom_linear = LinearProgressIndicatorStyle.default().copy_with(track_thickness=6.0)
    custom_circular = CircularProgressIndicatorStyle.default().copy_with(track_thickness=5.0)

    custom_theme = replace(
        light,
        extensions=[
            mat.copy_with(
                _linear_progress_indicator_style=custom_linear,
                _circular_progress_indicator_style=custom_circular,
            )
        ],
    )
    custom_mat = custom_theme.extension(MaterialThemeData)
    assert custom_mat is not None

    assert custom_mat.linear_progress_indicator_style.track_thickness == 6.0
    assert custom_mat.circular_progress_indicator_style.track_thickness == 5.0


def test_progress_style_from_theme_variants():
    light, _ = MaterialTheme.from_seed_pair("#6750A4")

    linear_default = LinearProgressIndicatorStyle.from_theme(light)
    linear_flat = LinearProgressIndicatorStyle.from_theme(light, "flat")
    circular_default = CircularProgressIndicatorStyle.from_theme(light)

    assert linear_default.track_thickness == 4.0
    assert linear_flat.wave_amplitude == 0.0
    assert circular_default.track_thickness == 4.0
