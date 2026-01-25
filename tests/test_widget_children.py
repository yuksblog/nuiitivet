from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_children import ChildContainerMixin


class Dummy(Widget):
    pass


def test_child_container_mixin_bypasses_overrides():
    class OwnerOverride(Widget):
        def __init__(self):
            super().__init__()
            self.override_called = False

        def add_child(self, widget):
            self.override_called = True

    owner = OwnerOverride()
    child = Dummy()

    ChildContainerMixin.add_child(owner, child)

    assert owner.override_called is False
    assert owner.children[0] is child
    assert getattr(child, "_parent", None) is owner
