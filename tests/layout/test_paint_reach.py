"""A container's paint visits only the children the clip reaches."""

from __future__ import annotations

from typing import Any, Callable, List, Sequence, Tuple

import pytest
import skia

from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.modifiers.transform import TransformBox, TransformModifier
from nuiitivet.observable import State
from nuiitivet.rendering.shadow import Shadow
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box

COUNT = 200


class _Leaf(Box):
    """A 100x50 leaf that counts how often a paint visits it."""

    def __init__(self) -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(50))
        self.visited = 0
        self.painted = 0
        self.outsets_read = 0

    def paint_outsets(self) -> Tuple[int, int, int, int]:
        self.outsets_read += 1
        return super().paint_outsets()

    def set_last_rect(self, x: int, y: int, width: int, height: int) -> None:
        self.visited += 1
        super().set_last_rect(x, y, width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1


def _canvas(width: int = 100, height: int = 100) -> Any:
    surface: Any = skia.Surface  # the local stub declares no constructor
    return surface(width, height).getCanvas()


def _visited(leaves: Sequence[_Leaf]) -> List[int]:
    return [i for i, leaf in enumerate(leaves) if leaf.visited]


def _column(leaves: Sequence[Widget]) -> Tuple[Widget, Tuple[int, int]]:
    return Column(children=leaves), (100, 50 * len(leaves))


def _row(leaves: Sequence[Widget]) -> Tuple[Widget, Tuple[int, int]]:
    return Row(children=list(leaves)), (100 * len(leaves), 50)


def _flow(leaves: Sequence[Widget]) -> Tuple[Widget, Tuple[int, int]]:
    # Two leaves per line.
    return Flow(children=leaves), (200, 25 * len(leaves))


def _uniform_flow(leaves: Sequence[Widget]) -> Tuple[Widget, Tuple[int, int]]:
    return UniformFlow(children=leaves, columns=2), (200, 25 * len(leaves))


_CONTAINERS: List[Callable[[Sequence[Widget]], Tuple[Widget, Tuple[int, int]]]] = [
    _column,
    _row,
    _flow,
    _uniform_flow,
]


@pytest.mark.parametrize("build", _CONTAINERS, ids=["column", "row", "flow", "uniform_flow"])
def test_a_paint_visits_only_the_children_near_the_clip(build) -> None:
    leaves = [_Leaf() for _ in range(COUNT)]
    container, (width, height) = build(leaves)
    container.layout(width, height)

    container.paint(_canvas(200, 100), 0, 0, width, height)

    # The clip shows the first 100px; the slack band reaches 32px past it.
    visited = _visited(leaves)
    assert visited and visited[0] == 0
    assert len(visited) <= 6


def test_a_grid_visits_every_child() -> None:
    leaves = [_Leaf() for _ in range(20)]
    items = [GridItem(leaf, row=i, column=0) for i, leaf in enumerate(leaves)]
    grid = Grid(items, rows=[50] * 20, columns=[100])
    grid.layout(100, 1000)

    grid.paint(_canvas(), 0, 0, 100, 1000)

    # A paint gives every item it visits a last rect.
    assert all(item.last_rect is not None for item in items)
    assert [i for i, leaf in enumerate(leaves) if leaf.painted] == [0, 1, 2]


def test_a_longer_list_visits_as_many_children() -> None:
    visits = []
    for count in (100, 10_000):
        leaves = [_Leaf() for _ in range(count)]
        column = Column(children=leaves)
        column.layout(100, 50 * count)
        column.paint(_canvas(), 0, 0, 100, 50 * count)
        visits.append(len(_visited(leaves)))

    assert visits[0] == visits[1]


def test_a_child_translated_into_view_after_the_layout_is_painted() -> None:
    leaf = _Leaf()
    translation: State[Tuple[float, float]] = State((0.0, 0.0))
    moved = TransformBox(leaf, translation=translation)
    column = Column(children=[*[_Leaf() for _ in range(9)], moved])
    column.layout(100, 500)
    column.paint(_canvas(), 0, 0, 100, 500)
    assert leaf.painted == 0

    translation.value = (0.0, -450.0)
    column.paint(_canvas(), 0, 0, 100, 500)

    assert leaf.painted == 1


def test_a_child_whose_shadow_grows_into_view_is_painted() -> None:
    leaves = [_Leaf() for _ in range(10)]
    column = Column(children=leaves)
    column.layout(100, 500)
    column.paint(_canvas(), 0, 0, 100, 500)
    assert leaves[9].painted == 0

    leaves[9].shadows = Shadow(color="#000000", offset=(0.0, -400.0))
    column.paint(_canvas(), 0, 0, 100, 500)

    assert leaves[9].painted == 1


def test_a_child_scrolled_out_of_reach_gives_up_its_last_rect() -> None:
    leaves = [_Leaf() for _ in range(20)]
    controller = ScrollController()
    viewport = ScrollViewport(
        child=Column(children=leaves),
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )
    viewport.layout(100, 100)
    canvas = _canvas()
    viewport.paint(canvas, 0, 0, 100, 100)
    assert leaves[0].last_rect is not None

    controller.scroll_to(600, axis=ScrollDirection.VERTICAL)
    viewport.paint(canvas, 0, 0, 100, 100)

    assert leaves[0].last_rect is None
    assert leaves[12].last_rect is not None


def test_a_child_whose_origin_moves_it_into_view_is_painted() -> None:
    leaf = _Leaf()
    # Scaled ten times from its top edge, it grows away from the clip.
    scaled = TransformBox(leaf, scale=10.0, transform_origin=(0.0, 0.0))
    column = Column(children=[*[_Leaf() for _ in range(9)], scaled])
    column.layout(100, 500)
    column.paint(_canvas(), 0, 0, 100, 500)
    assert leaf.painted == 0

    TransformModifier(transform_origin=(0.0, 50.0)).apply(scaled)
    column.paint(_canvas(), 0, 0, 100, 500)

    assert leaf.painted == 1


def test_a_moving_child_does_not_send_the_paint_through_every_sibling() -> None:
    siblings = [_Leaf() for _ in range(COUNT)]
    translation: State[Tuple[float, float]] = State((0.0, 0.0))
    column = Column(children=[*siblings, TransformBox(_Leaf(), translation=translation)])
    column.layout(100, 50 * (COUNT + 1))
    column.paint(_canvas(), 0, 0, 100, 50 * (COUNT + 1))
    before = sum(leaf.outsets_read for leaf in siblings)

    translation.value = (0.0, -10.0)
    column.paint(_canvas(), 0, 0, 100, 50 * (COUNT + 1))

    assert sum(leaf.outsets_read for leaf in siblings) - before <= 6


def test_a_child_moved_to_a_container_painted_first_keeps_its_last_rect() -> None:
    moved = _Leaf()
    first = Column(children=[_Leaf()])
    second = Column(children=[moved, _Leaf()])
    row = Row(children=[first, second])
    row.layout(200, 100)
    canvas = _canvas(200, 100)
    row.paint(canvas, 0, 0, 200, 100)

    second.remove_child(moved)
    first.add_child(moved)
    row.layout(200, 100)
    row.paint(canvas, 0, 0, 200, 100)

    assert moved.last_rect == (0, 50, 100, 50)


def test_the_widgets_below_a_child_scrolled_out_of_reach_give_up_their_last_rects() -> None:
    groups = [Column(children=[_Leaf(), _Leaf()]) for _ in range(10)]
    controller = ScrollController()
    viewport = ScrollViewport(
        child=Column(children=groups),
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )
    viewport.layout(100, 100)
    canvas = _canvas()
    viewport.paint(canvas, 0, 0, 100, 100)
    leaf = groups[0].children_snapshot()[0]
    assert leaf.last_rect is not None

    controller.scroll_to(600, axis=ScrollDirection.VERTICAL)
    viewport.paint(canvas, 0, 0, 100, 100)

    assert leaf.last_rect is None
