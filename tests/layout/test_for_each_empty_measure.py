"""A ``*.builder`` whose list is empty measures like an empty child list.

``expand_layout_children`` drops a provider that provides nothing. Kept as a
0x0 child, an empty ``ForEach`` made ``UniformFlow`` open one full-width
column for it, so an auto-width parent grew to the bound it was measured
under, and made ``Row`` / ``Column`` charge a gap for it.
"""

from __future__ import annotations

from typing import Tuple

from nuiitivet.layout.column import Column
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.row import Row
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.material.text import Text
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class _Box(Widget):
    def __init__(self, width: int, height: int) -> None:
        super().__init__()
        self._pref = (width, height)

    def preferred_size(self, max_width=None, max_height=None) -> Tuple[int, int]:
        return self._pref

    def paint(self, canvas, x, y, w, h) -> None:
        return None


def _tile(item: str, index: int) -> Widget:
    return Text(item, width=60, height=20)


def test_uniform_flow_builder_with_no_items_measures_padding_only() -> None:
    flow = UniformFlow.builder(Observable([]), _tile, columns=3, main_gap=8, cross_gap=8)

    assert flow.preferred_size() == (0, 0)
    assert flow.preferred_size(max_width=400) == (0, 0)
    assert flow.preferred_size(max_width=400, max_height=300) == (0, 0)


def test_uniform_flow_builder_with_no_items_and_padding_measures_the_padding() -> None:
    flow = UniformFlow.builder(Observable([]), _tile, columns=3, padding=(4, 2, 4, 2))

    assert flow.preferred_size(max_width=400) == (8, 4)


def test_bare_empty_provider_charges_no_gap_in_row_or_column() -> None:
    items: Observable = Observable([])

    column = Column([_Box(50, 10), ForEach(items, _tile), _Box(50, 10)], gap=6)
    row = Row([_Box(10, 50), ForEach(items, _tile), _Box(10, 50)], gap=6)

    assert column.preferred_size() == (50, 26)
    assert row.preferred_size() == (26, 50)


class _CardLikeScreen(ComposableWidget):
    """An auto-width column beside nothing, so its width is its content's."""

    def __init__(self, items: Observable) -> None:
        super().__init__()
        self.items = items

    def build(self) -> Widget:
        return Row(
            [
                Column(
                    [
                        Text("label", width=100, height=20),
                        UniformFlow.builder(self.items, _tile, columns=3, main_gap=8, key="flow"),
                    ],
                    gap=6,
                    cross_alignment="start",
                    key="column",
                ),
            ]
        )


def test_auto_width_parent_keeps_its_content_width_across_an_empty_refill(nuiitivet_app) -> None:
    """The regression as seen: the parent stays at content width on every layout pass."""

    screen = _CardLikeScreen(Observable([]))
    app = nuiitivet_app(screen, size=(600, 400))

    def widths() -> Tuple[int, int]:
        column = app.get(key="column").widget.layout_rect
        flow = app.get(key="flow").widget.layout_rect
        return (column[2], flow[2])

    assert widths() == (100, 0)

    screen.items.value = ["a", "b", "c"]
    app.settle()
    assert widths() == (196, 196)

    screen.items.value = []
    app.settle()
    assert widths() == (100, 0)

    app.settle()
    assert widths() == (100, 0)
