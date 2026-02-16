"""Test LoadingIndicatorStyle integration."""

from dataclasses import replace
from nuiitivet.material.loading_indicator import LoadingIndicator
from nuiitivet.material.styles import LoadingIndicatorStyle
from nuiitivet.material.shapes import MaterialShapeId
from nuiitivet.theme import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.animation.motion import BezierMotion


def test_loading_indicator_uses_theme_default_style():
    """LoadingIndicator without style parameter should use theme default."""
    light, _ = MaterialTheme.from_seed_pair("#00FF00")
    old_theme = manager.current
    try:
        manager.set_theme(light)
        indicator = LoadingIndicator(size=48)
        assert indicator.style is not None
        assert isinstance(indicator.style, LoadingIndicatorStyle)
        assert indicator.style.foreground == ColorRole.PRIMARY
        assert indicator.style.background is None
        assert indicator.style.active_size_ratio == 38.0 / 48.0
    finally:
        manager.set_theme(old_theme)


def test_loading_indicator_accepts_custom_style():
    """LoadingIndicator with style parameter should use provided style."""
    custom_style = LoadingIndicatorStyle(
        foreground=ColorRole.SECONDARY,
        active_size_ratio=0.9,
        motion=BezierMotion(0.34, 0.80, 0.34, 1.00, duration=3.0),
    )
    indicator = LoadingIndicator(size=64, style=custom_style)
    assert indicator._user_style is custom_style
    assert indicator.style.foreground == ColorRole.SECONDARY
    assert indicator.style.active_size_ratio == 0.9
    assert indicator.style.motion.duration == 3.0


def test_loading_indicator_style_copy_with():
    """LoadingIndicatorStyle can be customized with copy_with."""
    base = LoadingIndicatorStyle.default()
    custom = base.copy_with(
        foreground=ColorRole.TERTIARY,
        motion=BezierMotion(0.34, 0.80, 0.34, 1.00, duration=2.5),
    )
    assert custom.foreground == ColorRole.TERTIARY
    assert custom.motion.duration == 2.5
    assert custom.background is None
    assert custom.active_size_ratio == base.active_size_ratio


def test_theme_with_custom_loading_indicator_style():
    """Theme can provide custom loading indicator style."""
    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    custom_style = LoadingIndicatorStyle(
        foreground=ColorRole.ERROR,
        motion=BezierMotion(0.34, 0.80, 0.34, 1.00, duration=5.0),
        padding=8,
    )

    mat = light.extension(MaterialThemeData)
    assert mat is not None

    new_material = mat.copy_with(_loading_indicator_style=custom_style)
    custom_theme = replace(light, extensions=[new_material])

    old_theme = manager.current
    try:
        manager.set_theme(custom_theme)
        indicator = LoadingIndicator(size=48)
        assert indicator.style.foreground == ColorRole.ERROR
        assert indicator.style.motion.duration == 5.0
        assert indicator.style.padding == 8
    finally:
        manager.set_theme(old_theme)


def test_loading_indicator_style_variants():
    """LoadingIndicatorStyle provides default and contained variants."""
    default = LoadingIndicatorStyle.default()
    contained = LoadingIndicatorStyle.contained()

    assert default.foreground == ColorRole.PRIMARY
    assert default.background is None
    assert default.elevation == 0.0

    assert contained.foreground == ColorRole.PRIMARY
    assert contained.background == ColorRole.SURFACE_CONTAINER_HIGHEST
    assert contained.elevation == 1.0


def test_loading_indicator_style_from_theme():
    """LoadingIndicatorStyle.from_theme returns appropriate variant."""
    light, _ = MaterialTheme.from_seed_pair("#6750A4")

    default = LoadingIndicatorStyle.from_theme(light, "default")
    contained = LoadingIndicatorStyle.from_theme(light, "contained")

    assert default.background is None
    assert contained.background == ColorRole.SURFACE_CONTAINER_HIGHEST


def test_loading_indicator_padding_parameter():
    """LoadingIndicator accepts padding parameter."""
    indicator = LoadingIndicator(size=48, padding=16)
    # Padding is normalized to 4-tuple by Widget base class
    assert indicator._padding == (16, 16, 16, 16)

    indicator2 = LoadingIndicator(size=48, padding=(8, 12, 8, 12))
    assert indicator2._padding == (8, 12, 8, 12)


def test_loading_indicator_style_shapes():
    """LoadingIndicatorStyle can customize shapes sequence."""
    custom_shapes = (
        MaterialShapeId.PENTAGON,
        MaterialShapeId.OVAL,
    )
    style = LoadingIndicatorStyle(shapes=custom_shapes)
    indicator = LoadingIndicator(size=48, style=style)
    assert indicator.style.shapes == custom_shapes
