from nuiitivet.runtime.app import App
from nuiitivet.widgeting.widget import Widget
from nuiitivet.modifiers.focus import focusable
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import FocusNode, InteractionRegion


class TestWidget(Widget):
    __test__ = False

    def paint(self, canvas, x, y, w, h):
        pass


def test_focus_node_creation():
    w = TestWidget().modifier(focusable())
    assert isinstance(w, InteractionRegion)
    node = w.get_node(FocusNode)
    assert isinstance(node, FocusNode)


def test_focus_request_and_state():
    root = Box(width=100, height=100)
    child = TestWidget().modifier(focusable())
    root.add_child(child)

    app = App(root)
    # Mount the App root to ensure focus traversal sees the full tree.
    app.root.mount(app)

    node = child.get_node(FocusNode)
    assert not node.state.focused

    node.request_focus()
    assert node.state.focused
    assert app._focused_node is node

    app.root.unmount()


def test_focus_traversal():
    child1 = TestWidget().modifier(focusable())
    child2 = TestWidget().modifier(focusable())
    root = Box()
    root.add_child(child1)
    root.add_child(child2)

    app = App(root)
    app.root.mount(app)

    node1 = child1.get_node(FocusNode)
    node2 = child2.get_node(FocusNode)

    # Initial state
    assert not node1.state.focused
    assert not node2.state.focused

    # Tab -> Focus first
    app._dispatch_key_press("tab")
    assert node1.state.focused
    assert not node2.state.focused

    # Tab -> Focus second
    app._dispatch_key_press("tab")
    assert not node1.state.focused
    assert node2.state.focused

    # Tab -> Wrap around to first
    app._dispatch_key_press("tab")
    assert node1.state.focused
    assert not node2.state.focused

    app.root.unmount()


def test_key_event_routing():
    received_keys = []

    def on_key(key, modifiers):
        received_keys.append(key)
        return True

    child = TestWidget().modifier(focusable(on_key=on_key))
    root = Box()
    root.add_child(child)

    app = App(root)
    app.root.mount(app)

    node = child.get_node(FocusNode)
    node.request_focus()

    app._dispatch_key_press("a")
    assert received_keys == ["a"]

    app.root.unmount()


def test_key_event_bubbling():
    child_keys = []
    parent_keys = []

    def on_child_key(key, modifiers):
        child_keys.append(key)
        return False  # Bubble up

    def on_parent_key(key, modifiers):
        parent_keys.append(key)
        return True  # Handle it

    # Structure: Parent(Focusable) -> Child(Focusable)
    # Note: InteractionRegion wraps the widget.
    # To test bubbling, we need nested InteractionRegions.

    child = TestWidget().modifier(focusable(on_key=on_child_key))
    parent = Box().modifier(focusable(on_key=on_parent_key))
    parent.add_child(child)

    app = App(parent)
    app.root.mount(app)

    child_node = child.get_node(FocusNode)
    parent.get_node(FocusNode)

    # Focus child
    child_node.request_focus()
    assert child_node.state.focused

    # Dispatch key
    app._dispatch_key_press("b")

    assert child_keys == ["b"]
    assert parent_keys == ["b"]

    app.root.unmount()
