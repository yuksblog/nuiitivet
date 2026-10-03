"""A container reuses its laid-out child list, and skips culling inside a visible parent."""

from __future__ import annotations

from typing import Any, Callable, List, Sequence
from unittest.mock import MagicMock, patch

import pytest
import skia

from nuiitivet.layout import layout_utils
from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.rendering.skia import local_clip_bounds
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.testing import mount
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


class _Leaf(Box):
    def __init__(self, name: str = "") -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(50))
        self.name = name
        self.painted = 0

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1


def _canvas(width: int = 100, height: int = 100) -> Any:
    surface: Any = skia.Surface  # the local stub declares no constructor
    return surface(width, height).getCanvas()


def _painted(leaves: Sequence[Widget]) -> list[int]:
    return [i for i, leaf in enumerate(leaves) if getattr(leaf, "painted", 0)]


def _reset(leaves: Sequence[Any]) -> None:
    for leaf in leaves:
        leaf.painted = 0


def _grid(leaves: List[Widget]) -> Grid:
    return Grid(
        rows=[50] * len(leaves),
        columns=[100],
        children=[GridItem(leaf, row=i, column=0) for i, leaf in enumerate(leaves)],
    )


CONTAINERS: list[Callable[[List[Widget]], Any]] = [
    lambda leaves: Row(children=leaves),
    lambda leaves: Column(children=leaves),
    lambda leaves: Flow(children=leaves),
    lambda leaves: UniformFlow(leaves, columns=1),
    _grid,
]
IDS = ["row", "column", "flow", "uniform_flow", "grid"]


@pytest.mark.parametrize("make", CONTAINERS, ids=IDS)
def test_a_repaint_does_not_rebuild_the_child_list(make) -> None:
    leaves: List[Widget] = [_Leaf() for _ in range(3)]
    container = make(leaves)
    container.layout(400, 400)
    canvas = _canvas(400, 400)

    with patch.object(layout_utils, "expand_layout_children", wraps=layout_utils.expand_layout_children) as expand:
        container.paint(canvas, 0, 0, 400, 400)
        container.paint(canvas, 0, 0, 400, 400)

    assert expand.call_count == 0
    assert [leaf.painted for leaf in leaves] == [2, 2, 2]  # type: ignore[attr-defined]


@pytest.mark.parametrize("make", CONTAINERS, ids=IDS)
def test_a_paint_without_a_layout_lays_out_first(make) -> None:
    leaves: List[Widget] = [_Leaf() for _ in range(3)]
    container = make(leaves)

    container.paint(_canvas(400, 400), 0, 0, 400, 400)

    assert all(leaf.layout_rect is not None for leaf in leaves)
    assert _painted(leaves) == [0, 1, 2]


def test_an_added_child_is_painted_on_the_next_frame() -> None:
    leaves = [_Leaf() for _ in range(2)]
    column = Column(children=leaves)
    late = _Leaf()
    with mount(column, leak_check="off") as host:
        host.layout(400, 400)
        column.paint(_canvas(400, 400), 0, 0, 400, 400)

        column.add_child(late)
        host.settle()
        column.paint(_canvas(400, 400), 0, 0, 400, 400)

    assert late.painted == 1
    assert late.last_rect == (0, 100, 100, 50)


def test_a_removed_child_is_not_painted_again() -> None:
    leaves = [_Leaf() for _ in range(3)]
    column = Column(children=leaves)
    with mount(column, leak_check="off") as host:
        host.layout(400, 400)
        column.paint(_canvas(400, 400), 0, 0, 400, 400)
        _reset(leaves)

        column.remove_child(leaves[1])
        host.settle()
        column.paint(_canvas(400, 400), 0, 0, 400, 400)

    assert _painted(leaves) == [0, 2]
    assert leaves[2].last_rect == (0, 50, 100, 50)


def test_a_for_each_data_change_shows_on_the_next_frame() -> None:
    class _Model:
        names = Observable(["a", "b"])

    model = _Model()
    built: dict[str, _Leaf] = {}

    def build(name: str, _index: int) -> Widget:
        built[name] = _Leaf(name)
        return built[name]

    column = Column(children=[ForEach(model.names, build)])
    with mount(column, leak_check="off") as host:
        host.layout(400, 400)
        column.paint(_canvas(400, 400), 0, 0, 400, 400)
        assert sorted(name for name, leaf in built.items() if leaf.painted) == ["a", "b"]

        model.names.value = ["c", "a"]
        host.settle()
        _reset(list(built.values()))
        column.paint(_canvas(400, 400), 0, 0, 400, 400)

    assert sorted(name for name, leaf in built.items() if leaf.painted) == ["a", "c"]


def _clip_reads() -> Any:
    return patch.object(layout_utils, "local_clip_bounds", wraps=layout_utils.local_clip_bounds)


def test_containers_inside_the_clip_do_not_read_it_again() -> None:
    rows = [Row(children=[_Leaf(), _Leaf()]) for _ in range(3)]
    column = Column(children=rows)
    column.layout(400, 400)

    with _clip_reads() as reads:
        column.paint(_canvas(400, 400), 0, 0, 400, 400)

    assert reads.call_count == 1
    assert all(leaf.painted == 1 for row in rows for leaf in row.children)


def test_a_container_that_crosses_the_clip_still_culls() -> None:
    # Two 200px-tall groups on a 250px canvas: the first lies inside the clip,
    # the second crosses its bottom edge.
    first = [_Leaf() for _ in range(4)]
    second = [_Leaf() for _ in range(4)]
    column = Column(children=[Column(children=first), Column(children=second)])
    column.layout(100, 400)

    with _clip_reads() as reads:
        column.paint(_canvas(100, 250), 0, 0, 100, 400)

    assert _painted(first) == [0, 1, 2, 3]
    # Rows at 200 and 250 are near the clip; 300 and 350 are beyond the slack.
    assert _painted(second) == [0, 1]
    assert reads.call_count == 2


def test_a_scroll_viewport_inside_a_visible_parent_still_culls() -> None:
    leaves = [_Leaf() for _ in range(10)]
    viewport = ScrollViewport(
        child=Column(children=leaves),
        controller=ScrollController(),
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )
    column = Column(children=[viewport])
    column.layout(400, 400)

    column.paint(_canvas(400, 400), 0, 0, 400, 400)

    assert _painted(leaves) == [0, 1, 2]


def test_the_hint_covers_one_paint_only() -> None:
    leaves = [_Leaf() for _ in range(10)]
    column = Column(children=leaves)
    column.layout(100, 500)

    # As a parent would set it. Not culling is slower and still correct.
    column._paint_inside_clip = True
    column.paint(_canvas(), 0, 0, 100, 500)
    assert _painted(leaves) == list(range(10))
    assert column._paint_inside_clip is False

    _reset(leaves)
    column.paint(_canvas(), 0, 0, 100, 500)
    assert _painted(leaves) == [0, 1, 2]


def test_a_stand_in_canvas_has_no_readable_clip() -> None:
    assert local_clip_bounds(MagicMock()) is None
    assert local_clip_bounds(None) is None
    # Skia rounds the clip outwards by a pixel.
    assert local_clip_bounds(_canvas(40, 30)) == (-1.0, -1.0, 41.0, 31.0)
