"""Test Icon style parameter integration."""

from nuiitivet.material.icon import Icon
from nuiitivet.material.styles import IconStyle
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData


def test_icon_uses_theme_default_style():
    """Icon without style parameter should use theme default."""
    icon = Icon("home")
    assert icon.style is not None
    assert isinstance(icon.style, IconStyle)
    assert icon.style.default_size == 24
    assert icon.style.color == ColorRole.ON_SURFACE


def test_icon_accepts_custom_style():
    """Icon with style parameter should use provided style."""
    custom_style = IconStyle(
        default_size=32,
        color=ColorRole.PRIMARY,
        font_family_priority=(
            "Material Symbols Sharp",
            "Material Symbols Outlined",
        ),
    )
    icon = Icon("home", style=custom_style)
    assert icon.style is custom_style
    assert icon.style.default_size == 32
    assert icon.style.color == ColorRole.PRIMARY


def test_icon_style_get_font_family():
    """Icon should use style.get_font_family() for font selection."""
    custom_style = IconStyle(
        family="sharp",
        font_family_priority=(
            "Material Symbols Sharp",
            "Material Symbols Rounded",
            "Material Symbols Outlined",
        ),
    )
    icon = Icon("menu", style=custom_style)
    families = icon._candidate_families()
    assert "Material Symbols Sharp" in families
    assert "Material Symbols Rounded" in families
    assert "Material Symbols Outlined" in families


def test_icon_style_copy_with():
    """Icon style can be customized with copy_with."""
    base_style = IconStyle()
    custom_style = base_style.copy_with(default_size=40, color=ColorRole.SECONDARY)
    icon = Icon("star", style=custom_style)
    assert icon.style.default_size == 40
    assert icon.style.color == ColorRole.SECONDARY
    assert "Material Symbols Outlined" in icon.style.font_family_priority


def test_theme_with_custom_icon_style():
    """Theme can provide custom icon style."""
    custom_style = IconStyle(
        default_size=28,
        color=ColorRole.TERTIARY,
    )
    light, _ = MaterialThemeFactory.from_seed_pair("#FF0000")

    mat = light.extension(MaterialThemeData)
    assert mat is not None
    new_material = mat.copy_with(_icon_style=custom_style)
    assert new_material.icon_style.default_size == 28
    assert new_material.icon_style.color == ColorRole.TERTIARY


def test_icon_style_defaults():
    """Existing code without style parameter should continue working."""
    icon1 = Icon("home", size=24)
    assert icon1.style is not None
    icon2 = Icon("menu", size=32, padding=4)
    assert icon2.style is not None
    assert icon2.family == "outlined"


def test_icon_style_font_family_priority():
    """IconStyle font_family_priority should affect _candidate_families."""
    custom_style = IconStyle(
        font_family_priority=(
            "Material Icons",
            "Material Symbols Sharp",
            "Material Symbols Rounded",
            "Material Symbols Outlined",
        ),
    )
    icon = Icon("check", style=custom_style)
    families = icon._candidate_families()
    assert "Material Icons" in families
    assert "Material Symbols Sharp" in families
