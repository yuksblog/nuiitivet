"""Test Checkbox style parameter integration."""

from nuiitivet.material import Checkbox
from nuiitivet.material.styles import CheckboxStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.theme.resolver import resolve_color_to_rgba
from dataclasses import replace


def test_checkbox_uses_theme_default_style():
    """Checkbox without style parameter should use theme default."""
    checkbox = Checkbox()
    assert checkbox.style is not None
    assert isinstance(checkbox.style, CheckboxStyle)
    assert checkbox.style.default_touch_target == 48
    assert checkbox.style.icon_size_ratio == 18.0 / 48.0


def test_checkbox_accepts_custom_style():
    """Checkbox with style parameter should use provided style."""
    custom_style = CheckboxStyle(default_touch_target=56, icon_size_ratio=0.5, hover_alpha=0.15, pressed_alpha=0.2)
    checkbox = Checkbox(style=custom_style)
    assert checkbox.style is custom_style
    assert checkbox.style.default_touch_target == 56
    assert checkbox.style.icon_size_ratio == 0.5
    assert checkbox.style.hover_alpha == 0.15
    assert checkbox.style.pressed_alpha == 0.2


def test_checkbox_style_compute_sizes():
    """Checkbox should use style.compute_sizes() for layout."""
    custom_style = CheckboxStyle(icon_size_ratio=0.6, corner_radius_ratio=0.2, stroke_width_ratio=0.15)
    checkbox = Checkbox(style=custom_style)
    sizes = checkbox.style.compute_sizes(40)
    assert sizes["icon_size"] == 24
    assert abs(sizes["corner_radius"] - 4.8) < 0.01
    assert abs(sizes["stroke_width"] - 3.6) < 0.01


def test_checkbox_style_copy_with():
    """Checkbox style can be customized with copy_with."""
    base_style = CheckboxStyle()
    custom_style = base_style.copy_with(hover_alpha=0.2, pressed_alpha=0.3)
    checkbox = Checkbox(style=custom_style)
    assert checkbox.style.hover_alpha == 0.2
    assert checkbox.style.pressed_alpha == 0.3
    assert checkbox.style.icon_size_ratio == 18.0 / 48.0


def test_theme_with_custom_checkbox_style():
    """Theme can provide custom checkbox style."""
    custom_style = CheckboxStyle(default_touch_target=56, hover_alpha=0.1)
    light, _ = MaterialThemeFactory.from_seed_pair("#FF0000")

    mat_data = light.extension(MaterialThemeData)
    assert mat_data is not None
    new_mat_data = replace(mat_data, _checkbox_style=custom_style)
    assert new_mat_data.checkbox_style.default_touch_target == 56
    assert new_mat_data.checkbox_style.hover_alpha == 0.1


def test_checkbox_style_disabled_tokens_default_to_m3():
    """MD3 draws a disabled selection control from on-surface @ 38%, mark in surface."""
    style = CheckboxStyle()
    assert style.disabled_color == ColorRole.ON_SURFACE
    assert style.disabled_mark == ColorRole.SURFACE
    assert style.disabled_alpha == 0.38


def test_checkbox_style_resolve_colors_includes_disabled():
    """resolve_colors exposes the disabled colors alongside the enabled ones."""
    light, _ = MaterialThemeFactory.from_seed_pair("#6750A4")
    colors = CheckboxStyle().resolve_colors(theme=light)

    mat = light.extension(MaterialThemeData)
    assert mat is not None
    assert colors["disabled_color"] == resolve_color_to_rgba(mat.roles[ColorRole.ON_SURFACE])
    assert colors["disabled_mark"] == resolve_color_to_rgba(mat.roles[ColorRole.SURFACE])


def test_checkbox_touch_target_from_style():
    """Touch-target size is sourced from the style (MD3 fixes the axis)."""
    checkbox1 = Checkbox(checked=True)
    assert checkbox1.style is not None
    checkbox2 = Checkbox(
        checked=False, style=CheckboxStyle(default_touch_target=40), padding=8, disabled=True
    )
    assert checkbox2.style is not None
    assert checkbox2._touch_target_size == 40
