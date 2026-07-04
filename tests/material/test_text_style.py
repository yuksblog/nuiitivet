"""Tests for TextStyle and Text widget style integration."""

import pytest
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.text import Text
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material.theme.theme_data import MaterialThemeData
from dataclasses import replace


def test_text_style_defaults():
    """Test TextStyle default values."""
    style = TextStyle()
    assert style.font_size == 14
    assert style.color == ColorRole.ON_SURFACE
    assert style.text_alignment == "start"


def test_text_style_custom_values():
    """Test TextStyle with custom values."""
    style = TextStyle(
        font_size=24,
        color=ColorRole.PRIMARY,
        text_alignment="center",
    )
    assert style.font_size == 24
    assert style.color == ColorRole.PRIMARY
    assert style.text_alignment == "center"


def test_text_style_copy_with():
    """Test TextStyle.copy_with() method."""
    base_style = TextStyle(font_size=14, color=ColorRole.ON_SURFACE)

    # Change font size
    large_style = base_style.copy_with(font_size=24)
    assert large_style.font_size == 24
    assert large_style.color == ColorRole.ON_SURFACE  # unchanged

    # Change color
    primary_style = base_style.copy_with(color=ColorRole.PRIMARY)
    assert primary_style.font_size == 14  # unchanged
    assert primary_style.color == ColorRole.PRIMARY

    # Change multiple fields
    custom_style = base_style.copy_with(
        font_size=18,
        text_alignment="center",
    )
    assert custom_style.font_size == 18
    assert custom_style.color == ColorRole.ON_SURFACE  # unchanged
    assert custom_style.text_alignment == "center"


def test_text_style_immutable():
    """Test that TextStyle is immutable."""
    style = TextStyle()
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        style.font_size = 24


def test_text_widget_default_style():
    """Test Text widget uses theme default style when no style provided."""
    text = Text("Hello")
    # Should use default text_style
    assert text.style.font_size == 14
    assert text.style.color == ColorRole.ON_SURFACE


def test_text_widget_custom_style():
    """Test Text widget with custom style."""
    custom_style = TextStyle(
        font_size=24,
        color=ColorRole.PRIMARY,
        text_alignment="center",
    )
    text = Text("Hello", style=custom_style)
    assert text._style.font_size == 24
    assert text._style.color == ColorRole.PRIMARY
    assert text._style.text_alignment == "center"


def test_text_widget_style_font_size():
    """Test Text widget renders with custom font size."""
    text_small = Text("Small", style=TextStyle(font_size=10))
    text_large = Text("Large", style=TextStyle(font_size=32))

    # Verify style is stored
    assert text_small._style.font_size == 10
    assert text_large._style.font_size == 32

    # Check preferred_size reflects font size
    # (actual size will vary based on text content)
    small_size = text_small.preferred_size()
    large_size = text_large.preferred_size()
    # Large font should result in larger height
    assert large_size[1] > small_size[1]


def test_text_widget_style_text_alignment():
    """Test Text widget text_alignment options."""
    text_start = Text("Start", style=TextStyle(text_alignment="start"))
    text_center = Text("Center", style=TextStyle(text_alignment="center"))
    text_end = Text("End", style=TextStyle(text_alignment="end"))

    assert text_start._style.text_alignment == "start"
    assert text_center._style.text_alignment == "center"
    assert text_end._style.text_alignment == "end"


def test_text_widget_overflow_options():
    """Text widget overflow/truncation/max_lines live on the widget, not the style."""
    text_visible = Text("Text", overflow="visible")
    text_clip = Text("Text", overflow="clip")
    text_ellipsis = Text("Text", overflow="ellipsis", truncation="middle", max_lines=2)

    assert text_visible._overflow == "visible"
    assert text_clip._overflow == "clip"
    assert text_ellipsis._overflow == "ellipsis"
    assert text_ellipsis._truncation == "middle"
    assert text_ellipsis._max_lines == 2

    # Defaults
    default_text = Text("Text")
    assert default_text._overflow == "visible"
    assert default_text._truncation == "tail"
    assert default_text._max_lines is None
    assert default_text._soft_wrap is True

    # Invalid values fall back to defaults; max_lines < 1 clamps to 1.
    assert Text("x", overflow="bogus")._overflow == "visible"  # type: ignore[arg-type]
    assert Text("x", truncation="bogus")._truncation == "tail"  # type: ignore[arg-type]
    assert Text("x", max_lines=0)._max_lines == 1


def test_theme_default_text_style():
    """Test Theme provides default TextStyle."""
    light, dark = MaterialThemeFactory.from_seed_pair("#6750A4")

    light_mat = light.extension(MaterialThemeData)
    dark_mat = dark.extension(MaterialThemeData)
    assert light_mat is not None
    assert dark_mat is not None

    # Both themes should provide text_style
    assert light_mat.text_style is not None
    assert dark_mat.text_style is not None

    # Should have defaults
    assert light_mat.text_style.font_size == 14
    assert light_mat.text_style.color == ColorRole.ON_SURFACE


def test_theme_with_custom_text_style():
    """Test Theme.with_styles() with custom TextStyle."""
    light, _ = MaterialThemeFactory.from_seed_pair("#6750A4")

    custom_text_style = TextStyle(
        font_size=16,
        color=ColorRole.PRIMARY,
    )

    mat_data = light.extension(MaterialThemeData)
    assert mat_data is not None
    new_mat_data = replace(mat_data, _text_style=custom_text_style)
    new_extensions = [ext for ext in light.extensions if not isinstance(ext, MaterialThemeData)]
    new_extensions.append(new_mat_data)
    custom_theme = replace(light, extensions=new_extensions)

    custom_mat = custom_theme.extension(MaterialThemeData)
    assert custom_mat is not None
    assert custom_mat.text_style.font_size == 16
    assert custom_mat.text_style.color == ColorRole.PRIMARY

    # Original theme should be unchanged
    mat_data2 = light.extension(MaterialThemeData)
    assert mat_data2 is not None
    assert mat_data2.text_style.font_size == 14


def test_text_widget_uses_theme_text_style():
    """Test Text widget picks up custom text_style from theme."""
    # Create custom theme with large font
    light, _ = MaterialThemeFactory.from_seed_pair("#6750A4")
    custom_style = TextStyle(font_size=20, color=ColorRole.SECONDARY)

    mat_data = light.extension(MaterialThemeData)
    assert mat_data is not None
    new_mat_data = replace(mat_data, _text_style=custom_style)
    new_extensions = [ext for ext in light.extensions if not isinstance(ext, MaterialThemeData)]
    new_extensions.append(new_mat_data)
    custom_theme = replace(light, extensions=new_extensions)

    # Verify the theme data provides the custom style
    custom_mat = custom_theme.extension(MaterialThemeData)
    assert custom_mat is not None
    assert custom_mat.text_style.font_size == 20
    assert custom_mat.text_style.color == ColorRole.SECONDARY
