from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.widgeting.widget import Widget


class DummyWidget(Widget):

    def __init__(self, pref_w: int, pref_h: int, *, width=None, height=None, flex: int = 0):
        super().__init__(width=width, height=height)
        self._pref = (pref_w, pref_h)
        self.flex = flex

    def preferred_size(self):
        return self._pref

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


def test_row_fixed_width_respected():
    child_fixed = DummyWidget(10, 5, width=40)
    child_auto = DummyWidget(30, 5)
    row = Row([child_fixed, child_auto], gap=0)
    row.paint(None, 0, 0, 120, 40)
    fixed_rect = child_fixed.last_rect
    auto_rect = child_auto.last_rect
    assert fixed_rect is not None
    assert auto_rect is not None
    assert fixed_rect[2] == 40
    assert auto_rect[2] >= 30


def test_row_percent_stretch_distribution():
    left = DummyWidget(10, 5, width="50%")
    right = DummyWidget(15, 5, width="50%")
    row = Row([left, right], gap=0)
    row.paint(None, 0, 0, 200, 40)
    left_rect = left.last_rect
    right_rect = right.last_rect
    assert left_rect is not None
    assert right_rect is not None
    assert left_rect[2] == 100
    assert right_rect[2] == 100


def test_column_height_stretch():
    top = DummyWidget(10, 5, height="100%")
    col = Column([top])
    col.paint(None, 0, 0, 40, 150)
    top_rect = top.last_rect
    assert top_rect is not None
    assert top_rect[3] == 150


def test_column_auto_and_fixed_mix():
    fixed = DummyWidget(10, 5, height=60)
    auto = DummyWidget(10, 20)
    col = Column([fixed, auto], gap=0)
    col.paint(None, 0, 0, 40, 200)
    fixed_rect = fixed.last_rect
    auto_rect = auto.last_rect
    assert fixed_rect is not None
    assert auto_rect is not None
    assert fixed_rect[3] == 60
    assert auto_rect[3] >= 20


def test_row_negative_gap_normalized_in_preferred_size():
    a = DummyWidget(10, 5)
    b = DummyWidget(20, 5)
    row = Row([a, b], gap=-10)
    w, h = row.preferred_size()
    assert (w, h) == (30, 5)


def test_column_negative_gap_normalized_in_preferred_size():
    a = DummyWidget(10, 5)
    b = DummyWidget(10, 20)
    col = Column([a, b], gap=-10)
    w, h = col.preferred_size()
    assert (w, h) == (10, 25)
