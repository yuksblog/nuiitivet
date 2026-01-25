"""Tests for Widget.find_ancestor() method."""

from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.container import Container
from nuiitivet.layout.column import Column
from nuiitivet.widgets.box import Box


class CustomWidget(Widget):
    """Custom widget for testing."""

    def build(self):
        return self


def test_find_ancestor_direct_parent():
    """Test finding the immediate parent."""
    parent = Container()
    child = CustomWidget()
    parent.add_child(child)

    result = child.find_ancestor(Container)

    assert result is parent


def test_find_ancestor_grandparent():
    """Test finding a grandparent through multiple levels."""
    grandparent = Column([])
    parent = Container()
    child = CustomWidget()

    grandparent.add_child(parent)
    parent.add_child(child)

    result = child.find_ancestor(Column)

    assert result is grandparent


def test_find_ancestor_not_found():
    """Test when the requested type is not in the ancestor chain."""
    parent = Container()
    child = CustomWidget()
    parent.add_child(child)

    # Box is not in the ancestor chain
    result = child.find_ancestor(Box)

    assert result is None


def test_find_ancestor_root_widget():
    """Test finding ancestor when the widget is at the root."""
    root = CustomWidget()

    result = root.find_ancestor(Container)

    assert result is None


def test_find_ancestor_multiple_types():
    """Test finding different types in a complex hierarchy."""
    root = Column([])
    level1 = Container()
    level2 = Box()
    level3 = CustomWidget()

    root.add_child(level1)
    level1.add_child(level2)
    level2.add_child(level3)

    # Find Column (root)
    assert level3.find_ancestor(Column) is root

    # Find Container (level1)
    assert level3.find_ancestor(Container) is level1

    # Find Box (level2)
    assert level3.find_ancestor(Box) is level2

    # Find CustomWidget (not in ancestors, returns None)
    assert level3.find_ancestor(CustomWidget) is None


def test_find_ancestor_stops_at_first_match():
    """Test that find_ancestor returns the nearest ancestor of the specified type."""
    # Create a hierarchy with multiple Containers
    outer_container = Container()
    inner_container = Container()
    child = CustomWidget()

    outer_container.add_child(inner_container)
    inner_container.add_child(child)

    # Should return the inner (nearest) container
    result = child.find_ancestor(Container)

    assert result is inner_container
    assert result is not outer_container


def test_find_ancestor_with_widget_base_type():
    """Test finding the base Widget type."""
    parent = Container()
    child = CustomWidget()
    parent.add_child(child)

    # Container is a Widget, so this should work
    result = child.find_ancestor(Widget)

    assert result is parent


def test_find_ancestor_no_parent():
    """Test when widget has no parent set."""
    widget = CustomWidget()
    widget._parent = None

    result = widget.find_ancestor(Container)

    assert result is None
