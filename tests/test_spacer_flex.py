from nuiitivet.rendering.sizing import Sizing
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.row import Row
from nuiitivet.layout.spacer import Spacer
from nuiitivet.widgeting.widget import Widget


class DummyWidget(Widget):

    def __init__(self, pref_w: int, pref_h: int):
        super().__init__()
        self._pref = (pref_w, pref_h)

    def preferred_size(self):
        return self._pref

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


def test_flex_spacer_distribution_horizontal():
    items = ["a", "s", "b"]

    def builder(item, idx):
        if item == "s":
            return Spacer(width=Sizing.flex(1), height=Sizing.flex(1))
        return DummyWidget(20, 10)

    fe = ForEach(items, builder)
    fe.evaluate_build()
    row = Row([fe], gap=0)
    row.paint(None, 0, 0, 100, 50)
    spacer = fe.children[1]
    spacer_rect = spacer.last_rect
    assert spacer_rect is not None
    assert spacer_rect[2] == 60


def test_flex_spacer_multiple_factors():
    items = ["a", "s1", "s2", "b"]

    def builder(item, idx):
        if item == "s1":
            return Spacer(width=Sizing.flex(1), height=Sizing.flex(1))
        if item == "s2":
            return Spacer(width=Sizing.flex(3), height=Sizing.flex(3))
        return DummyWidget(10, 10)

    fe = ForEach(items, builder)
    fe.evaluate_build()
    row = Row([fe], gap=0)
    row.paint(None, 0, 0, 100, 50)
    s1 = fe.children[1]
    s2 = fe.children[2]
    s1_rect = s1.last_rect
    s2_rect = s2.last_rect
    assert s1_rect is not None
    assert s2_rect is not None
    assert s1_rect[2] == 20
    assert s2_rect[2] == 60
