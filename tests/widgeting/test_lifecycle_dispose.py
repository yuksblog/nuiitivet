"""Tests for Widget lifecycle (dispose) behavior."""

from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.container import Container


class LifecycleTracker(Widget):
    """Widget that tracks lifecycle events for testing."""

    events: list[str] = []  # Class variable to track all events

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def on_mount(self):
        LifecycleTracker.events.append(f"{self.name}:mount")
        super().on_mount()

    def on_unmount(self):
        LifecycleTracker.events.append(f"{self.name}:unmount")
        super().on_unmount()

    def build(self):
        return self


def test_unmount_parent_before_children():
    """Test that unmount() is called on parent before children."""
    LifecycleTracker.events = []  # Reset events

    # Create a hierarchy: root -> parent -> child
    root = LifecycleTracker("root")
    parent = LifecycleTracker("parent")
    child = LifecycleTracker("child")

    root.add_child(parent)
    parent.add_child(child)

    # Mount the entire tree
    root.mount("test_app")

    # Clear events from mount phase
    LifecycleTracker.events = []

    # Unmount from the root
    root.unmount()

    # Check that parent's unmount is called before child's
    assert LifecycleTracker.events == ["root:unmount", "parent:unmount", "child:unmount"]


def test_unmount_multiple_children_in_order():
    """Test that unmount() is called on children in their order."""
    LifecycleTracker.events = []

    root = LifecycleTracker("root")
    child1 = LifecycleTracker("child1")
    child2 = LifecycleTracker("child2")
    child3 = LifecycleTracker("child3")

    root.add_child(child1)
    root.add_child(child2)
    root.add_child(child3)

    root.mount("test_app")
    LifecycleTracker.events = []

    root.unmount()

    # Root's unmount should be called first, then children in order
    assert LifecycleTracker.events == [
        "root:unmount",
        "child1:unmount",
        "child2:unmount",
        "child3:unmount",
    ]


def test_unmount_nested_hierarchy():
    """Test unmount in a deeply nested hierarchy."""
    LifecycleTracker.events = []

    # Create a tree:
    # root
    #  ├─ level1a
    #  │   ├─ level2a
    #  │   └─ level2b
    #  └─ level1b

    root = LifecycleTracker("root")
    level1a = LifecycleTracker("level1a")
    level1b = LifecycleTracker("level1b")
    level2a = LifecycleTracker("level2a")
    level2b = LifecycleTracker("level2b")

    root.add_child(level1a)
    root.add_child(level1b)
    level1a.add_child(level2a)
    level1a.add_child(level2b)

    root.mount("test_app")
    LifecycleTracker.events = []

    root.unmount()

    # Expected order: root -> level1a -> level2a -> level2b -> level1b
    assert LifecycleTracker.events == [
        "root:unmount",
        "level1a:unmount",
        "level2a:unmount",
        "level2b:unmount",
        "level1b:unmount",
    ]


def test_unmount_clears_app_reference():
    """Test that unmount() clears the _app reference."""
    root = Container()
    child = Container()
    root.add_child(child)

    # Mount
    root.mount("test_app")
    assert root._app == "test_app"
    assert child._app == "test_app"

    # Unmount
    root.unmount()
    assert root._app is None
    assert child._app is None


def test_unmount_without_mount_is_safe():
    """Test that unmount() can be called on widgets that were never mounted."""
    widget = Container()
    child = Container()
    widget.add_child(child)

    # Should not raise an error
    widget.unmount()

    assert widget._app is None
    assert child._app is None


def test_mount_and_unmount_order():
    """Test that mount is called parent->child and unmount is called parent->child."""
    LifecycleTracker.events = []

    parent = LifecycleTracker("parent")
    child = LifecycleTracker("child")
    parent.add_child(child)

    # Mount
    parent.mount("test_app")
    mount_events = LifecycleTracker.events.copy()

    # Unmount
    LifecycleTracker.events = []
    parent.unmount()
    unmount_events = LifecycleTracker.events.copy()

    # Mount: parent first, then child
    assert mount_events == ["parent:mount", "child:mount"]

    # Unmount: parent first, then child (same order as mount)
    assert unmount_events == ["parent:unmount", "child:unmount"]
