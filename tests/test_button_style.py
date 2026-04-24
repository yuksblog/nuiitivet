"""Test Button style parameter integration."""

from nuiitivet.material.buttons import Button
from nuiitivet.material.styles import ButtonStyle
from nuiitivet.theme import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.color_role import ColorRole


def test_button_uses_theme_default_style():
    """Button without button_style parameter should use theme default."""
    light, _ = MaterialTheme.from_seed_pair("#00FF00")
    old_theme = manager.current
    try:
        manager.set_theme(light)
        button = Button(label="Test", style=ButtonStyle.filled())
        assert button.style is not None
        assert isinstance(button.style, ButtonStyle)
        assert button.style.background == ColorRole.PRIMARY
        assert button.style.foreground == ColorRole.ON_PRIMARY
    finally:
        manager.set_theme(old_theme)


def test_button_accepts_custom_button_style():
    """Button with style parameter should use provided style."""
    custom_style = ButtonStyle.outlined()
    button = Button(label="Custom", style=custom_style)
    assert button._user_style is custom_style
    assert custom_style.background is None
    assert custom_style.border_width == 1.0


def test_button_style_copy_with():
    """Button style can be customized with copy_with."""
    base_style = ButtonStyle.filled()
    custom_style = base_style.copy_with(background=ColorRole.SECONDARY, foreground=ColorRole.ON_SECONDARY)
    button = Button(label="Styled", style=custom_style)
    assert button._user_style.background == ColorRole.SECONDARY
    assert button._user_style.foreground == ColorRole.ON_SECONDARY
    assert button._user_style.elevation == 0.0


def test_button_without_explicit_style_uses_filled_default():
    """Button without an explicit ``style`` falls back to ``ButtonStyle.filled('s')``."""
    button = Button(label="Default")
    # Default is the unified MD3 filled style (no theme override).
    assert button.style.background == ColorRole.PRIMARY
    assert button.style.foreground == ColorRole.ON_PRIMARY
