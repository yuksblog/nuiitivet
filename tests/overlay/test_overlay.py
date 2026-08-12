"""Tests for Overlay widget."""

import pytest
from nuiitivet.overlay import Overlay, OverlayEntry
from nuiitivet.overlay.overlay import _OverlayEntryRoute
from nuiitivet.runtime.app import App
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


def test_overlay_of_falls_back_to_the_app_overlay():
    """The App's Overlay is a sibling of the Navigator, so no ancestor walk
    reaches it -- the fallback is what makes ``Overlay.of(self)`` work from a
    screen at all (#518)."""
    content = Container()
    app = App(content=content)
    app.root.mount(app)

    assert Overlay.of(content) is app.overlay


def test_overlay_of_prefers_a_nested_overlay_over_the_app_one():
    """The fallback must not shadow an intentionally nested Overlay."""
    nested = Overlay()
    widget = DummyWidget()
    nested.add_child(widget)
    app = App(content=nested)
    app.root.mount(app)

    assert Overlay.of(widget) is nested
    assert Overlay.of(widget, root=True) is app.overlay


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
    """Test that Overlay.of() with root=True returns the App's overlay."""
    content = Container()
    app = App(content=content)
    app.root.mount(app)

    found = Overlay.of(content, root=True)

    assert found is app.overlay


def test_overlay_of_not_found():
    """Test that Overlay.of() raises an error when no overlay is found."""
    widget = DummyWidget()
    # Attached, so the lookup fails for the reason under test (no Overlay above)
    # rather than for the pre-mount reason, which has its own message.
    Container().add_child(widget)

    with pytest.raises(RuntimeError, match="not attached to an App"):
        Overlay.of(widget)


def test_overlay_of_before_mount_reports_premature():
    """A pre-mount call names the timing, not a missing provider."""
    with pytest.raises(RuntimeError, match="before it was mounted"):
        Overlay.of(DummyWidget())


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
