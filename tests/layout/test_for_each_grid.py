from nuiitivet.layout.column import Column
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.layout.row import Row
from nuiitivet.widgeting import Widget


class DummyWidget(Widget):

    def __init__(self, pref_w: int, pref_h: int):
        super().__init__()
        self._pref = (pref_w, pref_h)

    def preferred_size(self):
        return self._pref

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


def test_row_builder_spreads_children():
    items = [0, 1, 2]

    def builder(item, idx):
        return DummyWidget((idx + 1) * 10, 8)

    row = Row.builder(items, builder, gap=2)
    fe = row.children[0]
    fe.evaluate_build()
    pref_w, pref_h = row.preferred_size()
    assert pref_w == 10 + 20 + 30 + 2 * (len(items) - 1)
    assert pref_h == 8
    row.paint(None, 0, 0, 200, 50)
    xs = []
    for child in fe.children:
        rect = child.last_rect
        assert rect is not None
        xs.append(rect[0])
    assert xs == [0, 12, 34]


def test_uniform_flow_builder_wraps_children():
    items = list(range(5))

    def builder(item, idx):
        return DummyWidget(20, 10)

    grid = UniformFlow.builder(items, builder, columns=2, cross_gap=4)
    fe = grid.children[0]
    fe.evaluate_build()
    grid.paint(None, 0, 0, 200, 200)
    rows = {}
    for idx, child in enumerate(fe.children):
        rect = child.last_rect
        assert rect is not None
        _, y, _, h = rect
        entry = rows.setdefault(y, {"indices": [], "height": h})
        entry["indices"].append(idx)
    assert len(rows) == 3
    ordered_rows = sorted(rows.items(), key=lambda kv: kv[0])
    first_row_y, first_entry = ordered_rows[0]
    second_row_y, _ = ordered_rows[1]
    assert second_row_y >= first_row_y + first_entry["height"] + grid.cross_gap


def test_column_builder_stacks_children():
    items = [0, 1, 2]

    def builder(item, idx):
        return DummyWidget(6 + idx * 2, (idx + 1) * 10)

    column = Column.builder(items, builder, gap=3)
    fe = column.children[0]
    fe.evaluate_build()

    pref_w, pref_h = column.preferred_size()
    assert pref_w == 10  # widest child width (idx=2)
    assert pref_h == (10 + 20 + 30) + column.gap * (len(items) - 1)

    column.paint(None, 0, 0, 50, 200)
    ys = []
    for child in fe.children:
        rect = child.last_rect
        assert rect is not None
        ys.append(rect[1])
    assert ys == [0, 13, 36]
