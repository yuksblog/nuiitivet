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


def test_children_is_the_same_tuple_until_a_mutation():
    owner = Dummy()
    first, second = Dummy(), Dummy()
    owner.add_child(first)

    before = owner.children
    assert owner.children is before

    owner.add_child(second)
    after = owner.children
    assert after is not before
    assert after == (first, second)
    assert before == (first,)

    owner.remove_child(first)
    assert owner.children == (second,)
