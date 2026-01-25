from nuiitivet.layout.flow import Flow
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


def test_flow_uniform_fixed_column_layout():
    children = [DummyWidget(20, 18) for _ in range(4)]
    layout = Flow(children, uniform=True, columns=2, main_gap=4, cross_gap=6)
    layout.paint(None, 0, 0, 200, 120)
    assert children[0].last_rect == (0, 0, 98, 18)
    assert children[1].last_rect == (102, 0, 98, 18)
    child2_rect = children[2].last_rect
    child3_rect = children[3].last_rect
    assert child2_rect is not None
    assert child3_rect is not None
    assert child2_rect[0] == 0
    assert child2_rect[1] == 24
    assert child3_rect[0] == 102
    assert child3_rect[1] == 24


def test_flow_uniform_max_extent_infers_columns():
    children = [DummyWidget(30, 12) for _ in range(3)]
    layout = Flow(children, uniform=True, max_column_width=70, main_gap=10)
    layout.paint(None, 0, 0, 220, 100)
    c0 = children[0].last_rect
    c1 = children[1].last_rect
    c2 = children[2].last_rect
    assert c0 is not None
    assert c1 is not None
    assert c2 is not None
    assert c0[2] == 105
    assert c1[0] == 115
    assert c2[1] > 0


def test_flow_uniform_applies_aspect_ratio():
    children = [DummyWidget(10, 10) for _ in range(2)]
    layout = Flow(children, uniform=True, columns=2, aspect_ratio=2.0, main_gap=0)
    layout.paint(None, 0, 0, 200, 200)
    c0 = children[0].last_rect
    c1 = children[1].last_rect
    assert c0 is not None
    assert c1 is not None
    assert c0[2] == 100
    assert c0[3] == 50
    assert c1[3] == 50
