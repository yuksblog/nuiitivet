"""Tests for AlertDialog widget."""

from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.styles.dialog_style import DialogStyle
from nuiitivet.theme.manager import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
import pytest


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


def test_alert_dialog_creation():
    """Test creating an AlertDialog."""
    dialog = AlertDialog(
        title="Test Title",
        message="Test Content",
    )

    assert dialog.title == "Test Title"
    assert dialog.message == "Test Content"
    assert dialog.actions == []


def test_alert_dialog_with_actions():
    """Test AlertDialog with action buttons."""
    from nuiitivet.material.buttons import TextButton

    actions = [
        TextButton("Cancel"),
        TextButton("OK"),
    ]

    dialog = AlertDialog(
        title="Confirm",
        message="Are you sure?",
        actions=actions,
    )

    assert len(dialog.actions) == 2


def test_alert_dialog_build():
    """Test building an AlertDialog."""
    dialog = AlertDialog(
        title="Title",
        message="Content",
    )

    # Build the widget tree
    built = dialog.build()

    # Should return a Box
    from nuiitivet.widgets.box import Box

    assert isinstance(built, Box)
    # Check default style usage via box properties

    # accessing via _background_color on Box because it stores it there
    # But Box might resolve it differently.
    # We can check simple properties if exposed.
    # Or just ensure it built.


def test_alert_dialog_minimal():
    """Test minimal AlertDialog (no title, content, or actions)."""
    dialog = AlertDialog()

    assert dialog.title is None
    assert dialog.message is None
    assert dialog.actions == []

    # Should still build successfully
    built = dialog.build()
    assert built is not None


def test_alert_dialog_style_override():
    """Test AlertDialog with custom style."""
    custom_style = DialogStyle(corner_radius=16.0, min_width=400.0, padding=32)

    dialog = AlertDialog(title="Props", style=custom_style)

    assert dialog.style.corner_radius == 16.0
    assert dialog.style.min_width == 400.0
    assert dialog.style.padding == 32


def test_alert_dialog_only_title():
    """Test AlertDialog with only title."""
    dialog = AlertDialog(
        title="Title only",
    )

    assert dialog.title is not None
    assert dialog.message is None
    assert dialog.actions == []


def test_alert_dialog_only_content():
    """Test AlertDialog with only content."""
    dialog = AlertDialog(
        message="Content only",
    )

    assert dialog.title is None
    assert dialog.message is not None


def test_alert_dialog_with_icon():
    """Test AlertDialog with icon."""
    dialog = AlertDialog(icon="home", title="With Icon")
    assert dialog.icon == "home"

    dialog.build()
    # Verification of built tree structure is hard without deep inspection
    # but at least it builds.
