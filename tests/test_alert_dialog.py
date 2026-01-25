"""Tests for AlertDialog widget."""

from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.theme.manager import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
import pytest


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


def test_alert_dialog_creation():
    """Test creating an AlertDialog."""
    dialog = AlertDialog(
        title=Text("Test Title"),
        content=Text("Test Content"),
    )

    assert dialog.title is not None
    assert dialog.content is not None
    assert dialog.actions == []


def test_alert_dialog_with_actions():
    """Test AlertDialog with action buttons."""
    from nuiitivet.material.buttons import TextButton

    actions = [
        TextButton("Cancel"),
        TextButton("OK"),
    ]

    dialog = AlertDialog(
        title=Text("Confirm"),
        content=Text("Are you sure?"),
        actions=actions,
    )

    assert len(dialog.actions) == 2


def test_alert_dialog_build():
    """Test building an AlertDialog."""
    dialog = AlertDialog(
        title=Text("Title"),
        content=Text("Content"),
    )

    # Build the widget tree
    built = dialog.build()

    # Should return a Box
    from nuiitivet.widgets.box import Box

    assert isinstance(built, Box)


def test_alert_dialog_minimal():
    """Test minimal AlertDialog (no title, content, or actions)."""
    dialog = AlertDialog()

    assert dialog.title is None
    assert dialog.content is None
    assert dialog.actions == []

    # Should still build successfully
    built = dialog.build()
    assert built is not None


def test_alert_dialog_properties():
    """Test AlertDialog properties."""
    dialog = AlertDialog(
        title=Text("Props"),
        width=400.0,
        padding=32,
        corner_radius=16.0,
    )

    assert dialog.width == 400.0
    assert dialog.padding == (32, 32, 32, 32)  # Normalized
    assert dialog.corner_radius == 16.0


def test_alert_dialog_only_title():
    """Test AlertDialog with only title."""
    dialog = AlertDialog(
        title=Text("Title only"),
    )

    assert dialog.title is not None
    assert dialog.content is None
    assert dialog.actions == []


def test_alert_dialog_only_content():
    """Test AlertDialog with only content."""
    dialog = AlertDialog(
        content=Text("Content only"),
    )

    assert dialog.title is None
    assert dialog.content is not None
    assert dialog.actions == []


def test_alert_dialog_only_actions():
    """Test AlertDialog with only actions."""
    from nuiitivet.material.buttons import TextButton

    actions = [TextButton("OK")]

    dialog = AlertDialog(
        actions=actions,
    )

    assert dialog.title is None
    assert dialog.content is None
    assert len(dialog.actions) == 1
