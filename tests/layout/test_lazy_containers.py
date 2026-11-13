"""Lazy containers: ``Column.lazy``, ``Row.lazy`` and ``UniformFlow.lazy``.

A lazy container holds a widget for each item its scroll viewport shows and
none for the others; its size on the scroll axis is the exact sum of its
items, so the scroll metrics need no estimate.
"""

from __future__ import annotations

from typing import Any, List

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.row import Row
from nuiitivet.layout.scrollable import HorizontalScrollable, VerticalScrollable
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.modifiers import on_unmount
from nuiitivet.observable import State
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgets.box import Box


class _App:
    def __init__(self) -> None:
        self.invalidations = 0
        self._pointer_capture_manager = PointerCaptureManager()

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidations += 1


class _Log:
    """Records which item indices the builder ran for and which items unmounted."""

    def __init__(self) -> None:
        self.built: List[int] = []
        self.unmounted: List[Any] = []

    def builder(self, item, index):
        self.built.append(index)
        return Box(width=Sizing.fixed(60), height=Sizing.fixed(20)).modifier(
            on_unmount(lambda item=item: self.unmounted.append(item))
        )


def _rects(container):
    return [child.layout_rect for child in container._laid_out_children]


def test_column_lazy_builds_only_the_items_in_view() -> None:
    log = _Log()
    column = Column.lazy(list(range(1000)), log.builder, gap=4)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)

    # Items are 20px with a 4px gap: five slots touch a 100px viewport.
    assert log.built == [0, 1, 2, 3, 4]
    assert _rects(column) == [(0, 0, 60, 20), (0, 24, 60, 20), (0, 48, 60, 20), (0, 72, 60, 20), (0, 96, 60, 20)]


def test_column_lazy_height_is_the_exact_sum_of_its_items() -> None:
    log = _Log()
    column = Column.lazy(list(range(1000)), log.builder, gap=4, padding=10)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)

    assert column.preferred_size(max_width=200) == (200, 1000 * 20 + 999 * 4 + 20)
    assert scroller._controller.content_size == 1000 * 20 + 999 * 4 + 20


def test_column_lazy_follows_the_scroll_offset() -> None:
    log = _Log()
    column = Column.lazy(list(range(1000)), log.builder, gap=4)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)
    log.built.clear()

    scroller._controller.scroll_to(24 * 500)
    assert column.needs_layout
    scroller.layout(200, 100)

    assert log.built == [500, 501, 502, 503, 504]
    assert _rects(column)[0] == (0, 12000, 60, 20)
    # The five items that scrolled out are gone.
    assert sorted(log.unmounted) == [0, 1, 2, 3, 4]
    provider = column.children_snapshot()[0]
    assert isinstance(provider, ForEach)
    assert len(provider.window_children()) == 5


def test_column_lazy_given_item_height_overrides_the_measured_one() -> None:
    log = _Log()
    column = Column.lazy(list(range(100)), log.builder, item_height=50)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)

    assert log.built == [0, 1]
    assert _rects(column) == [(0, 0, 60, 50), (0, 50, 60, 50)]
    assert column.preferred_size(max_width=200) == (200, 5000)


def test_column_lazy_keyed_insert_builds_only_the_newcomer() -> None:
    log = _Log()
    items: State[list[str]] = State([f"item {i}" for i in range(10)])
    column = Column.lazy(items, log.builder, key_fn=lambda item, index: item)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)
    log.built.clear()

    items.value = ["new", *items.value]
    scroller.layout(200, 100)

    assert log.built == [0]
    # The last of the five in view made room for the newcomer.
    assert log.unmounted == ["item 4"]
    assert column.preferred_size(max_width=200) == (200, 11 * 20)


def test_column_lazy_outside_a_scrollable_holds_the_items_inside_its_rect() -> None:
    log = _Log()
    column = Column.lazy(list(range(100)), log.builder, height=50)
    column.mount(_App())
    column.layout(200, 50)

    assert log.built == [0, 1, 2]


def test_column_lazy_with_auto_height_holds_every_item() -> None:
    log = _Log()
    column = Column.lazy(list(range(7)), log.builder)
    column.mount(_App())
    # A parent lays the column out at the length it answers, which is none
    # before the first pass; that pass measures the extent, and the parent's
    # next measure gets the whole length.
    column.layout(200, column.preferred_size()[1])
    assert column.preferred_size() == (60, 7 * 20)
    column.layout(200, column.preferred_size()[1])

    assert log.built == list(range(7))


@pytest.mark.parametrize(
    "make",
    [
        lambda log: Column.lazy(list(range(100)), log.builder),
        lambda log: Row.lazy(list(range(100)), log.builder),
        lambda log: UniformFlow.lazy(list(range(100)), log.builder, columns=4),
    ],
    ids=["column", "row", "uniform_flow"],
)
def test_preferred_size_of_a_lazy_container_builds_nothing(make) -> None:
    log = _Log()
    container = make(log)
    container.preferred_size()
    container.preferred_size(max_width=200, max_height=100)
    container.mount(_App())
    container.preferred_size(max_width=200)

    assert log.built == []


@pytest.mark.parametrize("item_height", [None, 20], ids=["measured", "given"])
def test_the_first_frame_shows_the_whole_length_on_the_scrollbar(item_height) -> None:
    log = _Log()
    column = Column.lazy(list(range(1000)), log.builder, gap=4, item_height=item_height)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)

    assert log.built == [0, 1, 2, 3, 4]
    assert scroller._controller.content_size == 1000 * 20 + 999 * 4
    assert scroller._controller.max_extent == 1000 * 20 + 999 * 4 - 100
    assert scroller._should_show_scrollbar()


def test_a_lazy_column_below_a_header_is_measured_through_its_parent() -> None:
    log = _Log()
    column = Column.lazy(list(range(1000)), log.builder)
    content = Column([Box(width=Sizing.fixed(60), height=Sizing.fixed(30)), column])
    scroller = VerticalScrollable(content, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)

    # The 70px below the header hold four 20px slots.
    assert log.built == [0, 1, 2, 3]
    assert content.layout_rect == (0, 0, 200, 30 + 1000 * 20)
    assert scroller._controller.content_size == 30 + 1000 * 20


def test_row_lazy_builds_only_the_items_in_view() -> None:
    log = _Log()
    row = Row.lazy(list(range(1000)), log.builder, gap=4)
    scroller = HorizontalScrollable(row, width=200, height=40)
    scroller.mount(_App())
    scroller.layout(200, 40)

    assert log.built == [0, 1, 2, 3]
    assert _rects(row) == [(0, 0, 60, 20), (64, 0, 60, 20), (128, 0, 60, 20), (192, 0, 60, 20)]
    assert row.preferred_size(max_height=40) == (1000 * 60 + 999 * 4, 40)

    log.built.clear()
    scroller._controller.scroll_to(64 * 10)
    scroller.layout(200, 40)
    assert log.built == [10, 11, 12, 13]


def test_uniform_flow_lazy_builds_only_the_rows_in_view() -> None:
    log = _Log()
    grid = UniformFlow.lazy(list(range(1000)), log.builder, columns=4, cross_gap=2)
    scroller = VerticalScrollable(grid, width=240, height=50)
    scroller.mount(_App())
    scroller.layout(240, 50)

    # Rows are 20px with a 2px gap: three rows of four touch a 50px viewport.
    assert log.built == list(range(12))
    assert _rects(grid)[:5] == [(0, 0, 60, 20), (60, 0, 60, 20), (120, 0, 60, 20), (180, 0, 60, 20), (0, 22, 60, 20)]
    assert grid.preferred_size(max_width=240) == (240, 250 * 20 + 249 * 2)
    assert len(grid.row_tracks) == 250

    log.built.clear()
    scroller._controller.scroll_to(22 * 100)
    scroller.layout(240, 50)
    assert log.built == list(range(400, 412))
    assert _rects(grid)[0] == (0, 2200, 60, 20)


def test_uniform_flow_lazy_row_height_from_aspect_ratio() -> None:
    log = _Log()
    grid = UniformFlow.lazy(list(range(100)), log.builder, columns=2, aspect_ratio=2.0)
    scroller = VerticalScrollable(grid, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)

    # 100px columns at 2:1 give 50px rows: two rows touch the viewport.
    assert log.built == [0, 1, 2, 3]
    assert grid.preferred_size(max_width=200) == (200, 50 * 50)


def test_for_each_window_holds_the_range_and_releases_the_rest() -> None:
    log = _Log()
    provider = ForEach(list(range(10)), log.builder)
    provider.set_window(2, 5)
    column = Column([provider])
    column.mount(_App())

    assert log.built == [2, 3, 4]
    assert len(provider.window_children()) == 3
    assert provider.item_count() == 10

    provider.set_window(4, 6)
    assert log.built == [2, 3, 4, 5]
    assert sorted(log.unmounted) == [2, 3]
