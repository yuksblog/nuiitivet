"""Tests for OverlayEntry."""

from nuiitivet.overlay import OverlayEntry
from nuiitivet.widgeting.widget import Widget


class DummyWidget(Widget):
    """Simple widget for testing."""

    def __init__(self):
        super().__init__()
        self.unmount_called = False

    def build(self):
        return self

    def unmount(self):
        self.unmount_called = True
        super().unmount()


def test_overlay_entry_creation():
    """Test creating an OverlayEntry."""

    def builder():
        return DummyWidget()

    entry = OverlayEntry(builder=builder)

    assert entry.builder is builder
    assert entry.is_visible is True
    assert entry._widget is None


def test_overlay_entry_build_widget():
    """Test building a widget from an entry."""
    widget = DummyWidget()

    def builder():
        return widget

    entry = OverlayEntry(builder=builder)

    # Build the widget
    result = entry.build_widget()

    assert result is widget
    assert entry._widget is widget


def test_overlay_entry_caches_widget():
    """Test that build_widget() caches the widget."""
    call_count = [0]

    def builder():
        call_count[0] += 1
        return DummyWidget()

    entry = OverlayEntry(builder=builder)

    # Build twice
    widget1 = entry.build_widget()
    widget2 = entry.build_widget()

    # Should be the same widget and builder called only once
    assert widget1 is widget2
    assert call_count[0] == 1


def test_overlay_entry_mark_for_removal():
    """Test marking an entry for removal."""

    def builder():
        return DummyWidget()

    entry = OverlayEntry(builder=builder)

    assert entry.is_visible is True

    entry.mark_for_removal()

    assert entry.is_visible is False


def test_overlay_entry_dispose():
    """Test disposing an entry."""
    widget = DummyWidget()

    def builder():
        return widget

    entry = OverlayEntry(builder=builder)
    entry.build_widget()  # Build the widget

    # Mount the widget first (simulate real usage)
    widget.mount("test_app")

    assert widget.unmount_called is False

    # Dispose the entry
    entry.dispose()

    # Widget should be unmounted
    assert widget.unmount_called is True
    assert entry._widget is None
    assert entry.is_visible is False


def test_overlay_entry_dispose_without_building():
    """Test disposing an entry that was never built."""

    def builder():
        return DummyWidget()

    entry = OverlayEntry(builder=builder)

    # Dispose without building
    entry.dispose()

    # Should not raise an error
    assert entry._widget is None
    assert entry.is_visible is False


def test_overlay_entry_dispose_handles_exceptions():
    """Test that dispose handles exceptions gracefully."""

    class BadWidget(Widget):
        def build(self):
            return self

        def unmount(self):
            raise RuntimeError("Unmount error")

    widget = BadWidget()

    def builder():
        return widget

    entry = OverlayEntry(builder=builder)
    entry.build_widget()

    # Should not raise an exception
    entry.dispose()

    assert entry._widget is None
    assert entry.is_visible is False
