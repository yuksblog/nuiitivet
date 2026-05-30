"""Tests for Widget.on_dispose() callback functionality."""

from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.container import Container


def test_on_dispose_callback_is_called():
    """Test that on_dispose() callback is called during unmount."""
    widget = Container()
    callback_called = []

    def callback():
        callback_called.append(True)

    widget.on_dispose(callback)

    # Mount and unmount
    widget.mount("test_app")
    widget.unmount()

    # Callback should have been called
    assert callback_called == [True]


def test_multiple_dispose_callbacks():
    """Test that multiple dispose callbacks can be registered and are all called."""
    widget = Container()
    callbacks_called = []

    def callback1():
        callbacks_called.append(1)

    def callback2():
        callbacks_called.append(2)

    def callback3():
        callbacks_called.append(3)

    widget.on_dispose(callback1)
    widget.on_dispose(callback2)
    widget.on_dispose(callback3)

    widget.mount("test_app")
    widget.unmount()

    # All callbacks should have been called in order
    assert callbacks_called == [1, 2, 3]


def test_dispose_callback_called_before_children_unmount():
    """Test that parent's dispose callbacks are called before children are unmounted."""
    events = []

    parent = Container()
    child = Container()
    parent.add_child(child)

    def parent_callback():
        events.append("parent_dispose_callback")

    parent.on_dispose(parent_callback)

    # Override child's on_unmount to track when it's called
    original_unmount = child.on_unmount

    def child_on_unmount():
        events.append("child_unmount")
        original_unmount()

    child.on_unmount = child_on_unmount

    parent.mount("test_app")
    parent.unmount()

    # Parent's dispose callback should be called before child's unmount
    assert events == ["parent_dispose_callback", "child_unmount"]


def test_dispose_callback_not_called_without_unmount():
    """Test that dispose callback is not called if widget is not unmounted."""
    widget = Container()
    callback_called = []

    def callback():
        callback_called.append(True)

    widget.on_dispose(callback)

    # Don't unmount, just let it be
    assert callback_called == []


def test_dispose_callback_exception_does_not_break_unmount():
    """Test that an exception in a dispose callback doesn't prevent other callbacks from running."""
    widget = Container()
    callbacks_called = []

    def callback1():
        callbacks_called.append(1)

    def callback_error():
        callbacks_called.append("error")
        raise RuntimeError("Test error")

    def callback2():
        callbacks_called.append(2)

    widget.on_dispose(callback1)
    widget.on_dispose(callback_error)
    widget.on_dispose(callback2)

    widget.mount("test_app")
    widget.unmount()

    # All callbacks should have been called despite the error
    assert callbacks_called == [1, "error", 2]


def test_dispose_callbacks_cleared_after_unmount():
    """Test that dispose callbacks are cleared after unmount."""
    widget = Container()
    callback_called = []

    def callback():
        callback_called.append(True)

    widget.on_dispose(callback)

    # First unmount
    widget.mount("test_app")
    widget.unmount()

    assert callback_called == [True]
    assert widget._dispose_callbacks == []

    # Second mount/unmount - callback should not be called again
    callback_called.clear()
    widget.mount("test_app")
    widget.unmount()

    assert callback_called == []


def test_dispose_callback_can_capture_widget_state():
    """Test that dispose callback can capture and use widget state."""
    widget = Container()
    widget.custom_data = "important_data"
    captured_data = []

    def callback():
        captured_data.append(widget.custom_data)

    widget.on_dispose(callback)

    widget.mount("test_app")
    widget.unmount()

    assert captured_data == ["important_data"]


def test_dispose_callback_called_after_on_unmount():
    """Test that dispose callbacks are called after on_unmount()."""
    events = []

    class CustomWidget(Widget):
        def on_unmount(self):
            events.append("on_unmount")
            super().on_unmount()

        def build(self):
            return self

    widget = CustomWidget()

    def callback():
        events.append("dispose_callback")

    widget.on_dispose(callback)

    widget.mount("test_app")
    widget.unmount()

    # on_unmount should be called first, then dispose callback
    assert events == ["on_unmount", "dispose_callback"]
