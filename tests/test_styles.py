"""Tests for widget style classes."""


def test_checkbox_style_defaults():
    """CheckboxStyle has correct M3 defaults."""
    from nuiitivet.material.styles import CheckboxStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = CheckboxStyle()
    assert style.default_touch_target == 48
    assert style.icon_size_ratio == 18.0 / 48.0
    assert style.stroke_color == ColorRole.ON_SURFACE
    assert style.checked_background == ColorRole.PRIMARY
    assert style.hover_alpha == 0.08
    assert style.pressed_alpha == 0.12


def test_checkbox_style_copy_with():
    """CheckboxStyle.copy_with() creates new instance with changes."""
    from nuiitivet.material.styles import CheckboxStyle

    original = CheckboxStyle()
    modified = original.copy_with(default_touch_target=56, hover_alpha=0.1)
    assert original.default_touch_target == 48
    assert modified.default_touch_target == 56
    assert original.hover_alpha == 0.08
    assert modified.hover_alpha == 0.1
    assert modified.pressed_alpha == 0.12


def test_checkbox_style_compute_sizes():
    """CheckboxStyle.compute_sizes() calculates correct pixel values."""
    from nuiitivet.material.styles import CheckboxStyle

    style = CheckboxStyle()
    sizes = style.compute_sizes(48)
    assert sizes["icon_size"] == 18
    assert sizes["corner_radius"] > 0
    assert sizes["stroke_width"] > 0
    assert sizes["state_layer_diameter"] == 40.0


def test_radio_button_style_defaults_and_compute_sizes():
    """RadioButtonStyle has sensible defaults and computes sizes."""
    from nuiitivet.material.styles import RadioButtonStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = RadioButtonStyle()
    assert style.default_touch_target == 48
    assert style.selected_stroke == ColorRole.PRIMARY
    sizes = style.compute_sizes(48)
    assert sizes["icon_diameter"] == 20
    assert sizes["inner_dot"] > 0


def test_switch_style_defaults_and_compute_sizes():
    """SwitchStyle has sensible defaults and computes sizes."""
    from nuiitivet.material.styles import SwitchStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = SwitchStyle()
    assert style.default_touch_target == 48
    assert style.checked_track == ColorRole.PRIMARY
    sizes = style.compute_sizes(48)
    assert sizes["track_width"] > sizes["track_height"]
    assert sizes["thumb_diameter"] > 0


def test_icon_style_defaults():
    """IconStyle has correct M3 defaults."""
    from nuiitivet.material.styles import IconStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = IconStyle()
    assert style.default_size == 24
    assert style.color == ColorRole.ON_SURFACE
    assert "Material Symbols Outlined" in style.font_family_priority


def test_icon_style_get_font_family():
    """IconStyle.get_font_family() returns correct family for style."""
    from nuiitivet.material.styles import IconStyle

    style = IconStyle()
    assert style.get_font_family("outlined") == "Material Symbols Outlined"
    assert style.get_font_family("rounded") == "Material Symbols Rounded"
    assert style.get_font_family("unknown") == "Material Symbols Outlined"


def test_button_style_defaults():
    """ButtonStyle has correct M3 defaults."""
    from nuiitivet.material.styles import ButtonStyle

    style = ButtonStyle()
    assert style.corner_radius == 20
    assert style.container_height == 40
    assert style.padding == (16, 0, 16, 0)
    assert style.min_width == 64
    assert style.min_height == 48
    assert style.elevation == 0.0


def test_button_style_filled():
    """ButtonStyle.filled() creates M3 Filled Button style."""
    from nuiitivet.material.styles import ButtonStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = ButtonStyle.filled()
    assert style.background == ColorRole.PRIMARY
    assert style.foreground == ColorRole.ON_PRIMARY
    assert style.border_width == 0.0
    assert style.elevation == 0.0


def test_button_style_outlined():
    """ButtonStyle.outlined() creates M3 Outlined Button style."""
    from nuiitivet.material.styles import ButtonStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = ButtonStyle.outlined()
    assert style.background is None
    assert style.foreground == ColorRole.PRIMARY
    assert style.border_color == ColorRole.OUTLINE
    assert style.border_width == 1.0


def test_button_style_text():
    """ButtonStyle.text() creates M3 Text Button style."""
    from nuiitivet.material.styles import ButtonStyle

    style = ButtonStyle.text()
    assert style.background is None
    assert style.padding == (16, 0, 16, 0)
    assert style.border_width == 0.0


def test_button_style_elevated():
    """ButtonStyle.elevated() creates M3 Elevated Button style."""
    from nuiitivet.material.styles import ButtonStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = ButtonStyle.elevated()
    assert style.background == ColorRole.SURFACE
    assert style.foreground == ColorRole.PRIMARY
    assert style.elevation == 1.0


def test_button_style_tonal():
    """ButtonStyle.tonal() creates M3 Filled Tonal Button style."""
    from nuiitivet.material.styles import ButtonStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = ButtonStyle.tonal()
    assert style.background == ColorRole.SECONDARY_CONTAINER
    assert style.foreground == ColorRole.ON_SECONDARY_CONTAINER


def test_style_classes_are_immutable():
    """All style classes are frozen dataclasses."""
    from nuiitivet.material.styles import ButtonStyle, CheckboxStyle, IconStyle, RadioButtonStyle, SwitchStyle

    button = ButtonStyle()
    checkbox = CheckboxStyle()
    icon = IconStyle()
    radio = RadioButtonStyle()
    switch = SwitchStyle()
    try:
        button.padding = 30
        assert False, "Should not be able to modify frozen dataclass"
    except Exception:
        pass
    try:
        checkbox.hover_alpha = 0.5
        assert False, "Should not be able to modify frozen dataclass"
    except Exception:
        pass
    try:
        icon.default_size = 32
        assert False, "Should not be able to modify frozen dataclass"
    except Exception:
        pass
    try:
        radio.icon_diameter_ratio = 1.0
        assert False, "Should not be able to modify frozen dataclass"
    except Exception:
        pass
    try:
        switch.track_width_ratio = 2.0
        assert False, "Should not be able to modify frozen dataclass"
    except Exception:
        pass
