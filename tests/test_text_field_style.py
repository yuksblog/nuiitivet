"""Test TextField style integration."""

from dataclasses import replace
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.theme import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData


def test_text_field_uses_theme_default_style():
    """TextField without style parameter should use theme default."""
    light, _ = MaterialTheme.from_seed_pair("#00FF00")
    old_theme = manager.current
    try:
        manager.set_theme(light)

        filled = TextField()
        assert filled.style is not None
        assert isinstance(filled.style, TextFieldStyle)
        # Filled default
        assert filled.style.container_color == ColorRole.SURFACE_CONTAINER_HIGHEST

        outlined = TextField(style=TextFieldStyle.outlined())
        assert outlined.style is not None
        # Outlined default
        assert outlined.style.container_color == (0, 0, 0, 0)
        assert outlined.style.indicator_color == ColorRole.OUTLINE
    finally:
        manager.set_theme(old_theme)


def test_text_field_accepts_custom_style():
    """TextField with style parameter should use provided style."""
    custom_style = TextFieldStyle.outlined().copy_with(border_radius=8.0)
    field = TextField(style=custom_style)
    assert field._user_style is custom_style
    assert field.style.border_radius == 8.0


def test_theme_with_custom_text_field_style():
    """Theme can override the default TextField style."""
    custom_filled = TextFieldStyle.filled().copy_with(border_radius=16.0)

    light, _ = MaterialTheme.from_seed_pair("#FF0000")

    mat = light.extension(MaterialThemeData)
    assert mat is not None
    new_material = mat.copy_with(_filled_text_field_style=custom_filled)
    custom_theme = replace(light, extensions=[new_material])

    old_theme = manager.current
    try:
        manager.set_theme(custom_theme)

        filled = TextField()
        assert filled.style.border_radius == 16.0
    finally:
        manager.set_theme(old_theme)
