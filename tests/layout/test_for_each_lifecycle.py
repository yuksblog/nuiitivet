"""Regression tests for ForEach mount/unmount lifecycle counts (issue #365).

ForEach used to fire ``on_mount`` / ``on_unmount`` on its item widgets far more
than the tree changes justified: every item mounted twice on the initial render,
and appending or inserting one item re-mounted every surviving item. These tests
pin the corrected behaviour — each structural change touches only the items that
actually entered or left, leaving survivors mounted in place.
"""

from __future__ import annotations

from typing import List

from nuiitivet.layout.column import Column
from nuiitivet.layout.for_each import ForEach
from nuiitivet.modifiers import on_mount, on_unmount
from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


class _DummyApp:
    def invalidate(self, immediate: bool = False) -> None:
        del immediate


def _mount_column(items: Observable) -> tuple[Column, List[str]]:
    log: List[str] = []

    def builder(item, index):
        del index
        return Box(width=Sizing.fixed(10), height=Sizing.fixed(10)).modifier(
            on_mount(lambda item=item: log.append(f"mount {item}"))
            | on_unmount(lambda item=item: log.append(f"unmount {item}"))
        )

    root = Column(children=[ForEach(items, builder, key_fn=lambda it, i: it)])
    root.mount(_DummyApp())
    return root, log


def test_initial_mount_fires_each_item_once() -> None:
    items = Observable([1, 2])
    _root, log = _mount_column(items)
    assert log == ["mount 1", "mount 2"]


def test_initial_mount_static_list_fires_each_item_once() -> None:
    # Confirms the double-mount was structural, not observable-subscription driven.
    _root, log = _mount_column(Observable([1, 2, 3]))
    assert log == ["mount 1", "mount 2", "mount 3"]


def test_append_leaves_survivors_mounted() -> None:
    items = Observable([1, 2])
    _root, log = _mount_column(items)
    log.clear()

    items.value = [1, 2, 3]
    assert log == ["mount 3"]


def test_insert_leaves_survivors_mounted() -> None:
    items = Observable([1, 2])
    _root, log = _mount_column(items)
    log.clear()

    items.value = [0, 1, 2]
    assert log == ["mount 0"]


def test_remove_unmounts_only_the_departed_item() -> None:
    items = Observable([1, 2, 3])
    _root, log = _mount_column(items)
    log.clear()

    items.value = [1, 2]
    assert log == ["unmount 3"]


def test_reorder_leaves_all_items_mounted() -> None:
    items = Observable([1, 2, 3])
    _root, log = _mount_column(items)
    log.clear()

    items.value = [3, 1, 2]
    assert log == []


def test_full_sequence_matches_expected_lifecycle() -> None:
    items = Observable([1, 2])
    _root, log = _mount_column(items)
    assert log == ["mount 1", "mount 2"]
    log.clear()

    items.value = [1, 2, 3]
    assert log == ["mount 3"]
    log.clear()

    items.value = [0, 1, 2, 3]
    assert log == ["mount 0"]
    log.clear()

    items.value = [0, 2, 3]
    assert log == ["unmount 1"]
    log.clear()

    items.value = [3, 2, 0]
    assert log == []
    log.clear()

    items.value = [2, 0]
    assert log == ["unmount 3"]
