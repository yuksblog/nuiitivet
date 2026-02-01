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


def test_flow_wrapping():
    # 200px width. Children 60px wide. 10px gap.
    # 3 items: 60, 60, 60. Gaps: 10, 10. Total: 200. Fits 3.
    children = [DummyWidget(60, 20) for _ in range(4)]
    layout = Flow(children, main_gap=10, cross_gap=10)
    layout.paint(None, 0, 0, 200, 100)

    # Check positions
    # Row 1: x=0, x=70, x=140
    assert children[0].last_rect == (0, 0, 60, 20)
    assert children[1].last_rect == (70, 0, 60, 20)
    assert children[2].last_rect == (140, 0, 60, 20)

    # Row 2: Wraps
    assert children[3].last_rect == (0, 30, 60, 20)  # 20 height + 10 gap = 30 y


def test_flow_alignment():
    # Test main alignment (center)
    children = [DummyWidget(50, 20)]
    layout = Flow(children, main_alignment="center")
    layout.paint(None, 0, 0, 200, 100)

    # 200 width, 50 content. Center = (200-50)/2 = 75
    assert children[0].last_rect == (75, 0, 50, 20)
