"""A ForEach window builds the items it is told to and holds the others' places."""

from __future__ import annotations

from typing import List

from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.spacer import Spacer
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


class _Log:
    def __init__(self) -> None:
        self.built: List[int] = []

    def builder(self, item, index):
        self.built.append(index)
        return Box(width=Sizing.fixed(60), height=Sizing.fixed(20))


def test_items_outside_the_build_range_get_a_placeholder():
    log = _Log()
    provider = ForEach(list(range(10)), log.builder)
    provider.set_window(0, 6, build=(0, 3))

    children = provider.window_children()
    assert len(children) == 6, "one child per item of the window"
    assert log.built == [0, 1, 2]
    assert provider.placeholder_indices() == [3, 4, 5]
    assert all(isinstance(child, Spacer) for child in children[3:])


def test_an_empty_build_range_holds_every_place():
    log = _Log()
    provider = ForEach(list(range(10)), log.builder)
    provider.set_window(0, 4, build=(0, 0))

    assert log.built == []
    assert provider.placeholder_indices() == [0, 1, 2, 3]


def test_build_item_replaces_the_placeholder_in_place():
    log = _Log()
    provider = ForEach(list(range(10)), log.builder)
    provider.set_window(0, 6, build=(0, 3))
    placeholder = provider.window_children()[4]

    built = provider.build_item(4)

    assert built is not None and built is provider.window_children()[4]
    assert placeholder not in provider.window_children(), "the placeholder left"
    assert placeholder.parent is None, "and was unmounted"
    assert log.built == [0, 1, 2, 4]
    assert provider.placeholder_indices() == [3, 5]
    assert provider.build_item(4) is built, "a built item is returned as it is"
    assert provider.build_item(9) is None, "outside the window"


def test_the_same_window_builds_the_placeholders_the_build_range_covers():
    log = _Log()
    provider = ForEach(list(range(10)), log.builder)
    provider.set_window(0, 6, build=(0, 3))

    provider.set_window(0, 6, build=(3, 5))
    assert log.built == [0, 1, 2, 3, 4]
    assert provider.placeholder_indices() == [5]


def test_a_change_of_the_items_builds_the_placeholders_too():
    from nuiitivet.layout.column import Column
    from nuiitivet.observable import State
    from nuiitivet.runtime.pointer import PointerCaptureManager

    class _App:
        def __init__(self) -> None:
            self._pointer_capture_manager = PointerCaptureManager()

        def invalidate(self, immediate: bool = False) -> None:
            del immediate

    log = _Log()
    items = State(list(range(10)))
    provider = ForEach(items, log.builder)
    provider.set_window(0, 6, build=(0, 3))
    column = Column([provider])
    column.mount(_App())

    items.value = list(range(100, 110))
    assert provider.placeholder_indices() == []
    assert len(provider.window_children()) == 6
    assert not any(isinstance(child, Spacer) for child in provider.window_children())


def test_a_window_without_a_build_range_builds_everything():
    log = _Log()
    provider = ForEach(list(range(10)), log.builder)
    provider.set_window(0, 6, build=(0, 3))

    provider.set_window(2, 7)
    assert sorted(log.built) == [0, 1, 2, 3, 4, 5, 6]
    assert provider.placeholder_indices() == []
