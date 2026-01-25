from nuiitivet.widgeting import Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row


class DummyWidget(Widget):
    """Test double that records paint calls and reports a fixed size."""

    def __init__(self, pref_w: int, pref_h: int):
        super().__init__()
        self._pref = (pref_w, pref_h)
        self.painted = False

    def preferred_size(self):
        return self._pref

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)
        self.painted = True


def test_row_allocation_and_hit_test():
    a = DummyWidget(80, 40)
    b = DummyWidget(80, 40)
    c = DummyWidget(80, 40)
    row = Row([a, b, c], gap=10, cross_alignment="center")
    canvas = object()
    row.paint(canvas, 0, 0, 320, 120)
    a_rect = a.last_rect
    b_rect = b.last_rect
    c_rect = c.last_rect
    assert a_rect is not None
    assert b_rect is not None
    assert c_rect is not None
    ax, ay, aw, ah = a_rect
    bx, by, bw, bh = b_rect
    cx, cy, cw, ch = c_rect
    assert aw > 0 and bw > 0 and (cw > 0)
    assert bx > ax
    assert cx > bx
    hit_a = row.hit_test(ax + aw // 2, ay + ah // 2)
    hit_b = row.hit_test(bx + bw // 2, by + bh // 2)
    hit_c = row.hit_test(cx + cw // 2, cy + ch // 2)
    assert hit_a is a
    assert hit_b is b
    assert hit_c is c


def test_column_allocation_and_alignment():
    a = DummyWidget(60, 20)
    b = DummyWidget(60, 20)
    col = Column([a, b], gap=5, cross_alignment="center")
    canvas = object()
    col.paint(canvas, 0, 0, 200, 200)
    a_rect = a.last_rect
    b_rect = b.last_rect
    assert a_rect is not None
    assert b_rect is not None
    ax, ay, aw, ah = a_rect
    bx, by, bw, bh = b_rect
    assert ax > 0
    assert bx > 0
    assert aw == 60 and bw == 60
    pref_w, pref_h = col.preferred_size()
    assert pref_w >= 60
    assert pref_h == 20 + 20 + 5
