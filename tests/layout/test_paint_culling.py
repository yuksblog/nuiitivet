"""Containers skip painting children the canvas clip would discard anyway."""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

import skia

from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.modifiers.transform import TransformBox
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


class _Leaf(Box):
    def __init__(self, outsets: Tuple[int, int, int, int] = (0, 0, 0, 0)) -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(50))
        self.painted = 0
        self._outsets = outsets

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1

    def paint_outsets(self) -> Tuple[int, int, int, int]:
        return self._outsets


def _canvas(width: int = 100, height: int = 100) -> Any:
    surface: Any = skia.Surface  # the local stub declares no constructor
    return surface(width, height).getCanvas()


def _painted(leaves: Sequence[Widget]) -> list[int]:
    return [i for i, leaf in enumerate(leaves) if getattr(leaf, "painted", 0)]


def test_column_paints_only_children_near_the_clip() -> None:
    # Ten 50px rows on a 100px-tall canvas: rows 0-1 are visible, row 2 sits
    # inside the slack band, and the rest are wholly below the clip.
    leaves = [_Leaf() for _ in range(10)]
    column = Column(children=leaves)
    column.layout(100, 500)

    column.paint(_canvas(), 0, 0, 100, 500)

    assert _painted(leaves) == [0, 1, 2]


def test_culled_children_still_get_their_last_rect() -> None:
    leaves = [_Leaf() for _ in range(10)]
    column = Column(children=leaves)
    column.layout(100, 500)

    column.paint(_canvas(), 0, 0, 100, 500)

    assert leaves[9].painted == 0
    assert leaves[9].last_rect == (0, 450, 100, 50)


def test_row_and_flow_cull_the_same_way() -> None:
    row_leaves: List[Widget] = [_Leaf() for _ in range(10)]
    row = Row(children=row_leaves)
    row.layout(1000, 50)
    row.paint(_canvas(), 0, 0, 1000, 50)
    assert _painted(row_leaves) == [0, 1]

    flow_leaves = [_Leaf() for _ in range(10)]
    flow = Flow(children=flow_leaves)
    flow.layout(100, 500)
    flow.paint(_canvas(), 0, 0, 100, 500)
    assert _painted(flow_leaves) == [0, 1, 2]


def test_without_a_readable_clip_every_child_paints() -> None:
    leaves = [_Leaf() for _ in range(10)]
    column = Column(children=leaves)
    column.layout(100, 500)

    column.paint(None, 0, 0, 100, 500)

    assert _painted(leaves) == list(range(10))


def test_scrolling_moves_the_painted_band() -> None:
    leaves = [_Leaf() for _ in range(10)]
    controller = ScrollController()
    viewport = ScrollViewport(
        child=Column(children=leaves),
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )
    viewport.layout(100, 100)
    controller.scroll_to(200, axis=ScrollDirection.VERTICAL)

    viewport.paint(_canvas(), 0, 0, 100, 100)

    # Rows 4-5 fill the viewport; rows 3 and 6 lie within the slack band.
    assert _painted(leaves) == [3, 4, 5, 6]


def test_paint_outsets_keep_an_overflowing_child_painted() -> None:
    # Row 9 lies far below the clip but reports that it paints 450px above
    # its rect, reaching back into view.
    leaves = [_Leaf() for _ in range(9)] + [_Leaf(outsets=(0, 450, 0, 0))]
    column = Column(children=leaves)
    column.layout(100, 500)

    column.paint(_canvas(), 0, 0, 100, 500)

    assert _painted(leaves) == [0, 1, 2, 9]


def test_a_translated_child_is_painted_where_it_lands() -> None:
    leaf = _Leaf()
    moved_up = TransformBox(leaf, translation=(0, -450))
    leaves = [_Leaf() for _ in range(9)]
    column = Column(children=[*leaves, moved_up])
    column.layout(100, 500)

    column.paint(_canvas(), 0, 0, 100, 500)

    assert leaf.painted == 1


def test_a_composable_reports_what_it_built() -> None:
    from nuiitivet.widgeting.widget import ComposableWidget

    class _Card(ComposableWidget):
        def build(self) -> Widget:
            return _Leaf(outsets=(0, 450, 0, 0))

    card = _Card()
    card.mount(None)
    try:
        assert card.paint_outsets() == (0, 450, 0, 0)
    finally:
        card.unmount()
