"""Tests for Snackbar widget and MaterialOverlay.snackbar() method."""

import pytest

from nuiitivet.observable import runtime
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.styles.snackbar_style import SnackbarStyle
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.overlay import Overlay
from nuiitivet.widgeting.widget import Widget


class MockClock:
    """Mock clock for testing snackbar auto-removal."""

    def __init__(self):
        self.scheduled = []
        self.current_time = 0.0

    def schedule_once(self, fn, delay):
        """Schedule a function to run after delay."""
        self.scheduled.append((self.current_time + delay, fn))
        self.scheduled.sort(key=lambda x: x[0])

    def unschedule(self, fn):
        """Unschedule a function."""
        self.scheduled = [(t, f) for t, f in self.scheduled if f != fn]

    def tick(self, delta):
        """Advance time and run scheduled functions."""
        self.current_time += delta
        to_run = []
        remaining = []

        for schedule_time, fn in self.scheduled:
            if schedule_time <= self.current_time + 1e-9:
                to_run.append((schedule_time, fn))
            else:
                remaining.append((schedule_time, fn))

        self.scheduled = remaining

        for _, fn in to_run:
            fn(0)


@pytest.fixture
def mock_clock(monkeypatch):
    """Provide a mock clock for testing."""
    clock = MockClock()
    monkeypatch.setattr(runtime, "clock", clock)
    return clock


def test_toast_creation():
    """Test creating a Snackbar widget."""
    snackbar = Snackbar(message="Test message")

    assert snackbar.message == "Test message"
    assert isinstance(snackbar.style, SnackbarStyle)
    assert snackbar.padding == (16, 16, 16, 16)


def test_toast_custom_style():
    """Test creating a Snackbar with custom style."""
    style = SnackbarStyle().copy_with(corner_radius=12.0, padding=20)
    snackbar = Snackbar(message="Custom", style=style)

    assert snackbar.style.corner_radius == 12.0
    assert snackbar.padding == (20, 20, 20, 20)


def test_toast_build():
    """Test building a Snackbar widget."""
    snackbar = Snackbar(message="Build test")

    # Build the widget
    built = snackbar.build()

    # Should return a Box widget
    from nuiitivet.widgets.box import Box

    assert isinstance(built, Box)


def test_overlay_toast_method():
    """Test MaterialOverlay.snackbar() method."""
    overlay = MaterialOverlay(intents={})

    # Show a snackbar
    overlay.snackbar("Test snackbar")

    # Should have one entry
    assert len(overlay._entry_to_route) == 1
    assert overlay.has_entries()


def test_overlay_toast_auto_removal(mock_clock):
    """Test that snackbar is automatically removed after duration."""
    overlay = MaterialOverlay(intents={})

    # Show a snackbar with short duration
    overlay.snackbar("Test snackbar", duration=0.1)

    # Should have one entry initially
    assert len(overlay._entry_to_route) == 1

    # Advance time past the duration
    mock_clock.tick(0.15)

    # Snackbar should be removed
    assert len(overlay._entry_to_route) == 0
    assert not overlay.has_entries()


def test_overlay_multiple_toasts():
    """Test showing multiple snackbars."""
    overlay = MaterialOverlay(intents={})

    # Show multiple toasts
    overlay.snackbar("First snackbar")
    overlay.snackbar("Second snackbar")
    overlay.snackbar("Third snackbar")

    # Should have three entries
    assert len(overlay._entry_to_route) == 3


def test_overlay_toast_custom_duration(mock_clock):
    """Test snackbar with custom duration."""
    overlay = MaterialOverlay(intents={})

    # Show toast with longer duration
    overlay.snackbar("Long snackbar", duration=5.0)

    assert len(overlay._entry_to_route) == 1

    # Advance time by 0.1 seconds
    mock_clock.tick(0.1)

    # Should still be visible
    assert len(overlay._entry_to_route) == 1

    # Advance time past the full duration
    mock_clock.tick(5.0)

    # Should be removed
    assert len(overlay._entry_to_route) == 0


def test_toast_widget_properties():
    """Test Snackbar widget properties."""
    snackbar = Snackbar(
        message="Props test",
        padding=20,
        style=SnackbarStyle().copy_with(corner_radius=12.0),
    )

    assert snackbar.padding == (20, 20, 20, 20)
    assert snackbar.style.corner_radius == 12.0


def test_overlay_toast_creates_entry():
    """Test that snackbar() creates a proper OverlayEntry."""
    overlay = MaterialOverlay(intents={})

    overlay.snackbar("Entry test")

    entry = next(iter(overlay._entry_to_route.keys()))

    # Build the widget from the entry
    built = entry.build_widget()

    def contains_type(root: Widget, t: type[Widget]) -> bool:
        if isinstance(root, t):
            return True
        try:
            children = root.children_snapshot()
        except Exception:
            children = getattr(root, "children", [])
        return any(contains_type(child, t) for child in children)

    assert contains_type(built, Snackbar)


def test_overlay_root_toast():
    """Test toast() on root overlay."""
    overlay = MaterialOverlay(intents={})
    Overlay.set_root(overlay)

    # Show toast on root overlay
    MaterialOverlay.root().snackbar("Root toast")

    assert len(overlay._entry_to_route) == 1

    # Cleanup
    Overlay._root_overlay = None
