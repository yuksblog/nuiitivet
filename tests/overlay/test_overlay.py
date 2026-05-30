"""Tests for Overlay widget."""

import pytest
from nuiitivet.overlay import Overlay, OverlayEntry
from nuiitivet.overlay.overlay import _OverlayEntryRoute
from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.container import Container


class DummyWidget(Widget):
    """Simple widget for testing."""

    def __init__(self, name: str = "dummy"):
        super().__init__()
        self.name = name

    def build(self):
        return self


def test_overlay_creation():
    """Test creating an Overlay widget."""
    overlay = Overlay()

    assert not overlay.has_entries()


def test_overlay_insert_entry():
    """Test inserting an entry into the overlay."""
    overlay = Overlay()
    entry = OverlayEntry(builder=lambda: DummyWidget("test"))

    overlay.insert_entry(entry)

    assert len(overlay._entry_to_route) == 1
    assert overlay.has_entries()
    assert isinstance(next(iter(overlay._entry_to_route.values())), _OverlayEntryRoute)


def test_overlay_remove_entry():
    """Test removing an entry from the overlay."""
    overlay = Overlay()
    entry = OverlayEntry(builder=lambda: DummyWidget("test"))

    overlay.insert_entry(entry)
    assert overlay.has_entries()

    overlay.remove_entry(entry)

    assert len(overlay._entry_to_route) == 0
    assert not overlay.has_entries()


def test_overlay_multiple_entries():
    """Test managing multiple entries."""
    overlay = Overlay()
    entry1 = OverlayEntry(builder=lambda: DummyWidget("entry1"))
    entry2 = OverlayEntry(builder=lambda: DummyWidget("entry2"))
    entry3 = OverlayEntry(builder=lambda: DummyWidget("entry3"))

    overlay.insert_entry(entry1)
    overlay.insert_entry(entry2)
    overlay.insert_entry(entry3)

    assert len(overlay._entry_to_route) == 3
    assert overlay.has_entries()


def test_overlay_insertion_order():
    """Test that entries are inserted in order (newer on top)."""
    overlay = Overlay()
    entry1 = OverlayEntry(builder=lambda: DummyWidget("first"))
    entry2 = OverlayEntry(builder=lambda: DummyWidget("second"))

    overlay.insert_entry(entry1)
    overlay.insert_entry(entry2)

    # Newer entry should be closed first.
    overlay.close_topmost()
    assert overlay.has_entries() is True
    overlay.close_topmost()
    assert overlay.has_entries() is False


def test_overlay_clear():
    """Test clearing all entries."""
    overlay = Overlay()
    entry1 = OverlayEntry(builder=lambda: DummyWidget("entry1"))
    entry2 = OverlayEntry(builder=lambda: DummyWidget("entry2"))

    overlay.insert_entry(entry1)
    overlay.insert_entry(entry2)

    overlay.clear()

    assert len(overlay._entry_to_route) == 0
    assert not overlay.has_entries()


def test_overlay_build_with_entries():
    """Test building the overlay widget tree with entries."""
    overlay = Overlay()
    widget1 = DummyWidget("widget1")
    widget2 = DummyWidget("widget2")

    entry1 = OverlayEntry(builder=lambda: widget1)
    entry2 = OverlayEntry(builder=lambda: widget2)

    overlay.insert_entry(entry1)
    overlay.insert_entry(entry2)

    # Build the overlay
    built = overlay.build()

    assert isinstance(built, Widget)


def test_overlay_build_without_entries():
    """Test building the overlay when it's empty."""
    overlay = Overlay()

    # Build the overlay
    built = overlay.build()

    assert isinstance(built, Widget)


def test_overlay_root_not_set():
    """Test that Overlay.root() raises an error when not set."""
    # Reset the root overlay
    Overlay._root_overlay = None

    with pytest.raises(RuntimeError, match="No root overlay found"):
        Overlay.root()


def test_overlay_set_and_get_root():
    """Test setting and getting the root overlay."""
    overlay = Overlay()

    Overlay.set_root(overlay)

    assert Overlay.root() is overlay

    # Cleanup
    Overlay._root_overlay = None


def test_overlay_of_finds_ancestor():
    """Test that Overlay.of() finds an ancestor overlay."""
    overlay = Overlay()
    container = Container()
    widget = DummyWidget()

    # Create hierarchy: overlay -> container -> widget
    overlay.add_child(container)
    container.add_child(widget)

    # Find the overlay from the widget
    found = Overlay.of(widget)

    assert found is overlay


def test_overlay_of_root_flag():
    """Test that Overlay.of() with root=True returns the root overlay."""
    root_overlay = Overlay()
    Overlay.set_root(root_overlay)

    widget = DummyWidget()

    # Get the root overlay
    found = Overlay.of(widget, root=True)

    assert found is root_overlay

    # Cleanup
    Overlay._root_overlay = None


def test_overlay_of_not_found():
    """Test that Overlay.of() raises an error when no overlay is found."""
    widget = DummyWidget()

    with pytest.raises(RuntimeError, match="No Overlay found in the widget tree"):
        Overlay.of(widget)


def test_overlay_has_entries_with_invisible_entry():
    """Test has_entries() when an entry is marked as invisible."""
    overlay = Overlay()
    entry = OverlayEntry(builder=lambda: DummyWidget("test"))

    overlay.insert_entry(entry)
    assert overlay.has_entries()

    # Mark the entry as invisible
    entry.mark_for_removal()

    # has_entries() should return False
    assert not overlay.has_entries()


def test_overlay_entry_dispose_is_idempotent() -> None:
    dispose_calls = 0

    def on_dispose() -> None:
        nonlocal dispose_calls
        dispose_calls += 1

    entry = OverlayEntry(builder=lambda: DummyWidget("idempotent"), on_dispose=on_dispose)
    entry.build_widget()

    entry.dispose()
    entry.dispose()

    assert dispose_calls == 1
