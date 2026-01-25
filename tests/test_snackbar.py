"""Tests for Snackbar widget and MaterialOverlay.snackbar() method."""

import pytest

from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.material.styles.snackbar_style import SnackbarStyle
from nuiitivet.observable import runtime
from nuiitivet.overlay import Overlay
from nuiitivet.widgeting.widget import Widget


class MockClock:
    """Mock clock for testing snackbar auto-removal."""

    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []
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


def test_snackbar_creation() -> None:
    snackbar = Snackbar(message="Test message")

    assert snackbar.message == "Test message"
    assert isinstance(snackbar.style, SnackbarStyle)
    assert snackbar.padding == (16, 16, 16, 16)


def test_snackbar_custom_style() -> None:
    style = SnackbarStyle().copy_with(corner_radius=12.0, padding=20)
    snackbar = Snackbar(message="Custom", style=style)

    assert snackbar.style.corner_radius == 12.0
    assert snackbar.padding == (20, 20, 20, 20)


def test_snackbar_build() -> None:
    snackbar = Snackbar(message="Build test")

    built = snackbar.build()

    from nuiitivet.widgets.box import Box

    assert isinstance(built, Box)


def test_material_overlay_snackbar_method() -> None:
    overlay = MaterialOverlay(intents={})

    overlay.snackbar("Test snackbar")

    assert len(overlay._entry_to_route) == 1
    assert overlay.has_entries()


def test_material_overlay_snackbar_auto_removal(mock_clock) -> None:
    overlay = MaterialOverlay(intents={})

    overlay.snackbar("Test snackbar", duration=0.1)

    assert len(overlay._entry_to_route) == 1

    mock_clock.tick(0.15)

    assert len(overlay._entry_to_route) == 0
    assert not overlay.has_entries()


def test_material_overlay_multiple_snackbars() -> None:
    overlay = MaterialOverlay(intents={})

    overlay.snackbar("First snackbar")
    overlay.snackbar("Second snackbar")
    overlay.snackbar("Third snackbar")

    assert len(overlay._entry_to_route) == 3


def test_material_overlay_snackbar_custom_duration(mock_clock) -> None:
    overlay = MaterialOverlay(intents={})

    overlay.snackbar("Long snackbar", duration=5.0)

    assert len(overlay._entry_to_route) == 1

    mock_clock.tick(0.1)
    assert len(overlay._entry_to_route) == 1

    mock_clock.tick(5.0)
    assert len(overlay._entry_to_route) == 0


def test_snackbar_widget_properties() -> None:
    snackbar = Snackbar(
        message="Props test",
        padding=20,
        style=SnackbarStyle().copy_with(corner_radius=12.0),
    )

    assert snackbar.padding == (20, 20, 20, 20)
    assert snackbar.style.corner_radius == 12.0


def test_material_overlay_snackbar_creates_entry() -> None:
    overlay = MaterialOverlay(intents={})

    overlay.snackbar("Entry test")

    entry = next(iter(overlay._entry_to_route.keys()))
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


def test_material_overlay_root_snackbar() -> None:
    overlay = MaterialOverlay(intents={})
    Overlay.set_root(overlay)

    MaterialOverlay.root().snackbar("Root snackbar")

    assert len(overlay._entry_to_route) == 1

    Overlay._root_overlay = None
