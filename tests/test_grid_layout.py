import pytest

from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.widgeting.widget import Widget


class DummyWidget(Widget):

    def __init__(self, pref_w: int, pref_h: int):
        super().__init__()
        self._pref = (pref_w, pref_h)
        self.clear_last_rect()

    def preferred_size(self):
        return self._pref

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


def test_grid_requires_explicit_coordinates():
    # Provide dummy rows/cols to satisfy __init__, but GridItem is missing column
    grid = Grid(children=[GridItem(DummyWidget(10, 10), row=0)], rows=[], columns=[])
    with pytest.raises(ValueError):
        grid.preferred_size()


def test_grid_places_items_in_fixed_tracks():
    child = DummyWidget(20, 15)
    grid = Grid(
        rows=[80],
        columns=[120],
        padding=8,
        children=[GridItem(child, row=0, column=0)],
    )
    grid.paint(None, 0, 0, 400, 200)
    assert child.last_rect == (8, 8, 20, 15)


def test_grid_area_mapping_creates_spans():
    header = DummyWidget(100, 30)
    sidebar = DummyWidget(80, 60)
    content = DummyWidget(150, 120)
    grid = Grid.named_areas(
        children=[
            GridItem.named_area(header, name="header"),
            GridItem.named_area(sidebar, name="sidebar"),
            GridItem.named_area(content, name="content"),
        ],
        areas=[
            ["header", "header"],
            ["sidebar", "content"],
            ["sidebar", "content"],
        ],
        rows=["auto", "auto", "auto"],
        columns=["auto", "auto"],
        row_gap=5,
        column_gap=5,
    )
    w, h = grid.preferred_size()
    assert w > 0 and h > 0
    grid.paint(None, 0, 0, w + 50, h + 50)
    # Sidebar should start at column 0 and span two rows, header should span both columns
    header_rect = header.last_rect
    sidebar_rect = sidebar.last_rect
    assert header_rect is not None
    assert sidebar_rect is not None
    assert header_rect[2] >= sidebar_rect[2]
    assert sidebar_rect[3] >= 60


def test_grid_auto_tracks_expand_to_fit_content():
    left = DummyWidget(60, 40)
    right = DummyWidget(60, 40)
    grid = Grid(
        rows=["auto"],
        columns=["auto", "auto"],
        row_gap=0,
        column_gap=10,
        children=[
            GridItem(left, row=0, column=0),
            GridItem(right, row=0, column=1),
        ],
    )
    w, h = grid.preferred_size()
    # Preferred width should be both items + spacing
    assert w >= 60 + 60 + 10
    grid.paint(None, 0, 0, w, h)
    left_rect = left.last_rect
    right_rect = right.last_rect
    assert left_rect is not None
    assert right_rect is not None
    assert left_rect[2] >= 60
    assert right_rect[2] >= 60
