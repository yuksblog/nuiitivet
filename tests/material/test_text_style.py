"""Tests for TextStyle, TypeScale tokens and Text widget integration.

Layer model (see docs/design/TYPOGRAPHY.md):
- Typography (font size / line height / weight / tracking) -> TypeScaleToken.
- Layout / flow (alignment, overflow, ...) -> Text widget.
- Reusable visual look (color, font_family) -> TextStyle.
"""

import pytest
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.text import Text
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.theme.type_scale import DEFAULT_TYPE_SCALE, TypeScale, TypeScaleToken
from dataclasses import replace


# --- TextStyle (visual look only) -----------------------------------------


def test_text_style_defaults():
    """TextStyle carries only color + font_family."""
    style = TextStyle()
    assert style.color == ColorRole.ON_SURFACE
    assert style.font_family is None


def test_text_style_no_typography_or_alignment():
    """Typography and alignment must not live on TextStyle anymore."""
    style = TextStyle()
    assert not hasattr(style, "font_size")
    assert not hasattr(style, "text_alignment")


def test_text_style_copy_with():
    """TextStyle.copy_with() replaces visual fields."""
    base = TextStyle(color=ColorRole.ON_SURFACE)
    primary = base.copy_with(color=ColorRole.PRIMARY)
    assert primary.color == ColorRole.PRIMARY
    assert base.color == ColorRole.ON_SURFACE  # unchanged

    with_family = base.copy_with(font_family="Roboto")
    assert with_family.font_family == "Roboto"


def test_text_style_immutable():
    """TextStyle is frozen."""
    style = TextStyle()
    with pytest.raises(Exception):  # FrozenInstanceError
        style.color = ColorRole.PRIMARY  # type: ignore[misc]


# --- TypeScaleToken --------------------------------------------------------


def test_type_scale_roles_values():
    """A few MD3 roles carry the expected metrics."""
    assert TypeScale.TITLE_MEDIUM == TypeScaleToken(16, 24, 500, 0.15)
    assert TypeScale.BODY_MEDIUM == TypeScaleToken(14, 20, 400, 0.25)
    assert TypeScale.LABEL_LARGE == TypeScaleToken(14, 20, 500, 0.1)
    assert TypeScale.DISPLAY_LARGE.tracking == -0.25  # negative tracking allowed


def test_type_scale_token_copy_with():
    """Single-metric tweaks live on the token."""
    heavy = TypeScale.TITLE_MEDIUM.copy_with(weight=700)
    assert heavy.weight == 700
    assert heavy.font_size == 16  # unchanged
    assert TypeScale.TITLE_MEDIUM.weight == 500  # original unchanged


def test_type_scale_token_from_size():
    """from_size() builds a full token from a raw numeric size."""
    tok = TypeScaleToken.from_size(18)
    assert tok.font_size == 18
    assert tok.line_height == 18 * 1.25
    assert tok.weight == 400
    assert tok.tracking == 0.0

    explicit = TypeScaleToken.from_size(10, line_height=14, weight=500)
    assert explicit.line_height == 14
    assert explicit.weight == 500


def test_type_scale_token_immutable():
    """Tokens are frozen."""
    with pytest.raises(Exception):
        TypeScale.BODY_MEDIUM.font_size = 99  # type: ignore[misc]


# --- Text widget integration ----------------------------------------------


def test_text_widget_default_type_scale():
    """Text without an explicit type_scale falls back to Body Medium."""
    text = Text("Hello")
    assert text.type_scale == DEFAULT_TYPE_SCALE
    assert text.type_scale.font_size == 14


def test_text_widget_explicit_type_scale():
    """Explicit type_scale drives typography."""
    text = Text("Hello", type_scale=TypeScale.HEADLINE_SMALL)
    assert text.type_scale.font_size == 24


def test_text_widget_alignment_on_widget():
    """Alignment is a widget param, not a style field."""
    assert Text("Start", alignment="start")._alignment == "start"
    assert Text("Center", alignment="center")._alignment == "center"
    assert Text("End", alignment="end")._alignment == "end"
    # Default + invalid fallback.
    assert Text("Default")._alignment == "start"
    assert Text("x", alignment="bogus")._alignment == "start"  # type: ignore[arg-type]


def test_text_widget_font_size_affects_preferred_height():
    """Larger type-scale font size yields a taller preferred size."""
    small = Text("Small", type_scale=TypeScaleToken.from_size(10))
    large = Text("Large", type_scale=TypeScaleToken.from_size(32))
    assert large.preferred_size()[1] > small.preferred_size()[1]


def test_text_widget_custom_style_color():
    """Custom TextStyle stores color."""
    text = Text("Hello", style=TextStyle(color=ColorRole.PRIMARY))
    assert text._style.color == ColorRole.PRIMARY


def test_text_widget_overflow_options():
    """Overflow/truncation/max_lines live on the widget, not the style."""
    text_ellipsis = Text("Text", overflow="ellipsis", truncation="middle", max_lines=2)
    assert text_ellipsis._overflow == "ellipsis"
    assert text_ellipsis._truncation == "middle"
    assert text_ellipsis._max_lines == 2

    default_text = Text("Text")
    assert default_text._overflow == "visible"
    assert default_text._truncation == "tail"
    assert default_text._max_lines is None
    assert default_text._soft_wrap is True

    assert Text("x", overflow="bogus")._overflow == "visible"  # type: ignore[arg-type]
    assert Text("x", truncation="bogus")._truncation == "tail"  # type: ignore[arg-type]
    assert Text("x", max_lines=0)._max_lines == 1


# --- Theme integration -----------------------------------------------------


def test_theme_default_text_style():
    """Theme provides a default (color-only) TextStyle."""
    light, dark = MaterialThemeFactory.from_seed_pair("#6750A4")
    light_mat = light.extension(MaterialThemeData)
    dark_mat = dark.extension(MaterialThemeData)
    assert light_mat is not None and dark_mat is not None
    assert light_mat.text_style.color == ColorRole.ON_SURFACE


def test_theme_with_custom_text_style():
    """Theme can carry a custom color TextStyle."""
    light, _ = MaterialThemeFactory.from_seed_pair("#6750A4")
    custom_text_style = TextStyle(color=ColorRole.PRIMARY)

    mat_data = light.extension(MaterialThemeData)
    assert mat_data is not None
    new_mat_data = replace(mat_data, _text_style=custom_text_style)
    new_extensions = [ext for ext in light.extensions if not isinstance(ext, MaterialThemeData)]
    new_extensions.append(new_mat_data)
    custom_theme = replace(light, extensions=new_extensions)

    custom_mat = custom_theme.extension(MaterialThemeData)
    assert custom_mat is not None
    assert custom_mat.text_style.color == ColorRole.PRIMARY

    # Original unchanged.
    mat_data2 = light.extension(MaterialThemeData)
    assert mat_data2 is not None
    assert mat_data2.text_style.color == ColorRole.ON_SURFACE
