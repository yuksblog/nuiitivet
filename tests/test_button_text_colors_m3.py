"""Test that button text colors comply with Material Design 3 specifications.

M3 Button Text Color Specifications:
- FilledButton: ON_PRIMARY
- OutlinedButton: PRIMARY
- TextButton: PRIMARY
- ElevatedButton: ON_SURFACE
- FilledTonalButton: ON_SURFACE_VARIANT
- FloatingActionButton (FAB): ON_PRIMARY
"""

from nuiitivet.material.buttons import (
    FilledButton,
    OutlinedButton,
    TextButton,
    ElevatedButton,
    FilledTonalButton,
    FloatingActionButton,
)
from nuiitivet.material.text import Text
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.theme.manager import manager
from nuiitivet.material.styles.text_style import TextStyle
import pytest


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


def test_filled_button_text_color():
    """FilledButton should use ON_PRIMARY for text per M3 spec."""
    btn = FilledButton("Test")
    assert len(btn.children) == 1
    text_widget = btn.children[0]
    assert isinstance(text_widget, Text)
    assert text_widget.style.color == ColorRole.ON_PRIMARY


def test_outlined_button_text_color():
    """OutlinedButton should use PRIMARY for text per M3 spec."""
    btn = OutlinedButton("Test")
    assert len(btn.children) == 1
    text_widget = btn.children[0]
    assert isinstance(text_widget, Text)
    assert text_widget.style.color == ColorRole.PRIMARY


def test_text_button_text_color():
    """TextButton should use PRIMARY for text per M3 spec."""
    btn = TextButton("Test")
    assert len(btn.children) == 1
    text_widget = btn.children[0]
    assert isinstance(text_widget, Text)
    assert text_widget.style.color == ColorRole.PRIMARY


def test_elevated_button_text_color():
    """ElevatedButton should use PRIMARY for text per M3 spec."""
    btn = ElevatedButton("Test")
    assert len(btn.children) == 1
    text_widget = btn.children[0]
    assert isinstance(text_widget, Text)
    assert text_widget.style.color == ColorRole.PRIMARY


def test_filled_tonal_button_text_color():
    """FilledTonalButton should use ON_SECONDARY_CONTAINER for text per M3 spec."""
    btn = FilledTonalButton("Test")
    assert len(btn.children) == 1
    text_widget = btn.children[0]
    assert isinstance(text_widget, Text)
    assert text_widget.style.color == ColorRole.ON_SECONDARY_CONTAINER


def test_fab_text_color():
    """FloatingActionButton should use ON_PRIMARY for text per M3 spec."""
    btn = FloatingActionButton("Test")
    assert len(btn.children) == 1
    child = btn.children[0]
    from nuiitivet.material.icon import Icon

    assert isinstance(child, Icon)
    assert child.style.color == ColorRole.ON_PRIMARY


def test_text_widget_default_color():
    """Text widget without explicit color should default to ON_SURFACE."""
    text = Text("Test")
    assert text.style.color == ColorRole.ON_SURFACE


def test_text_widget_custom_color():
    """Text widget should accept custom color via style."""
    text = Text("Test", style=TextStyle(color=ColorRole.PRIMARY))
    assert text.style.color == ColorRole.PRIMARY
    text_hex = Text("Test", style=TextStyle(color="#FF0000"))
    assert text_hex._style.color == "#FF0000"
