from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.widget import Widget


class DummyWidget(Widget):
    def __init__(self, pref_w: int, pref_h: int, *, width: SizingLike = None, height: SizingLike = None):
        super().__init__(width=width, height=height)
        self._pref = (pref_w, pref_h)
        self.clear_last_rect()

    def preferred_size(self, max_width=None, max_height=None):
        return self._pref

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


def test_uniform_fixed_column_layout():
    children = [DummyWidget(20, 18, width="wt") for _ in range(4)]
    layout = UniformFlow(children, columns=2, main_gap=4, cross_gap=6)
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


def test_uniform_max_extent_infers_columns():
    children = [DummyWidget(30, 12, width="wt") for _ in range(3)]
    layout = UniformFlow(children, max_column_width=70, main_gap=10)
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


def test_uniform_applies_aspect_ratio():
    children = [DummyWidget(10, 10, width="wt", height="wt") for _ in range(2)]
    layout = UniformFlow(children, columns=2, aspect_ratio=2.0, main_gap=0)
    layout.paint(None, 0, 0, 200, 200)
    c0 = children[0].last_rect
    c1 = children[1].last_rect
    assert c0 is not None
    assert c1 is not None
    assert c0[2] == 100
    assert c0[3] == 50
    assert c1[3] == 50


def test_auto_child_keeps_its_size_and_sits_at_start_by_default():
    children = [DummyWidget(20, 18), DummyWidget(20, 18)]
    layout = UniformFlow(children, columns=2)
    layout.paint(None, 0, 0, 200, 100)
    assert children[0].last_rect == (0, 0, 20, 18)
    assert children[1].last_rect == (100, 0, 20, 18)


def test_item_alignment_positions_an_auto_child_in_its_cell():
    children = [DummyWidget(20, 10), DummyWidget(20, 30)]
    layout = UniformFlow(children, columns=2, item_alignment=("end", "center"))
    layout.paint(None, 0, 0, 200, 100)
    assert children[0].last_rect == (80, 10, 20, 10)
    assert children[1].last_rect == (180, 0, 20, 30)


def test_weight_child_fills_its_cell_whatever_the_alignment():
    children = [DummyWidget(20, 10, width="wt", height="wt"), DummyWidget(20, 30)]
    layout = UniformFlow(children, columns=2, item_alignment="center")
    layout.paint(None, 0, 0, 200, 100)
    assert children[0].last_rect == (0, 0, 100, 30)
    assert children[1].last_rect == (140, 0, 20, 30)


def test_fixed_height_child_keeps_its_height_in_a_taller_row():
    short = DummyWidget(20, 10, width="wt", height=50)
    tall = DummyWidget(20, 80, width="wt")
    layout = UniformFlow([short, tall], columns=2, item_alignment="center")
    layout.paint(None, 0, 0, 200, 200)
    assert short.last_rect == (0, 15, 100, 50)
    assert tall.last_rect == (100, 0, 100, 80)


def test_a_row_is_as_tall_as_its_tallest_child_measures():
    with_fixed = [DummyWidget(20, 90, width="wt", height="wt"), DummyWidget(20, 10, width="wt", height=40)]
    layout = UniformFlow(with_fixed, columns=2)
    assert layout.preferred_size(max_width=200) == (200, 90)
    layout.paint(None, 0, 0, 200, 90)
    assert with_fixed[0].last_rect == (0, 0, 100, 90)
    assert with_fixed[1].last_rect == (100, 0, 100, 40)


def test_rows_of_weight_heights_share_the_spare_height():
    children = [DummyWidget(20, 90, width="wt", height="wt") for _ in range(4)]
    layout = UniformFlow(children, columns=2, cross_gap=4)
    assert layout.preferred_size(max_width=200) == (200, 184)
    layout.paint(None, 0, 0, 200, 205)
    assert children[0].last_rect == (0, 0, 100, 101)
    assert children[2].last_rect == (0, 105, 100, 100)

    mixed = [DummyWidget(20, 10, width="wt", height=40), DummyWidget(20, 10), DummyWidget(20, 90, height="wt")]
    layout = UniformFlow(mixed, columns=2, cross_gap=4, item_alignment="center")
    layout.paint(None, 0, 0, 200, 200)
    assert mixed[0].last_rect == (0, 0, 100, 40)
    assert mixed[2].last_rect == (40, 44, 20, 156)


def test_uniform_flow_passes_column_constraint_to_children():
    """Test that children receive column width constraint (Height-for-Width)."""
    from typing import Tuple, Optional

    class WidthWrappingWidget(Widget):
        def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
            # if constrained to <= 100, height doubles
            if max_width is not None and max_width <= 100:
                return (100, 200)
            return (200, 100)

        def layout(self, width: int, height: int) -> None:
            self._test_rect = (0, 0, width, height)
            super().layout(width, height)

    child1 = WidthWrappingWidget(width="wt", height="auto")
    child2 = WidthWrappingWidget(width="wt", height="auto")

    # 2 columns in 200px width -> 100px per column
    flow = UniformFlow([child1, child2], columns=2, width=200, padding=0, main_gap=0)

    flow.layout(200, 500)

    # Check that children measured with max_width=100 and got height 200
    assert hasattr(child1, "_test_rect")
    _, _, w, h = child1._test_rect
    assert w == 100
    assert h == 200

    # The flow should also have sized itself to contain height 200
    flow_pref = flow.preferred_size(max_width=200)
    assert flow_pref[1] == 200


def test_fixed_width_uniform_flow_measures_columns_against_its_own_width():
    # Fixed width 200, columns at most 100 wide: two columns, two rows.
    children = [DummyWidget(60, 20) for _ in range(4)]
    flow = UniformFlow(children, max_column_width=100, width=200)

    two_rows = (200, 40)
    assert flow.preferred_size() == two_rows
    assert flow.preferred_size(max_width=200) == two_rows
    assert flow.preferred_size(max_width=600) == two_rows

    # A narrower parent still wins: one column, four rows.
    assert flow.preferred_size(max_width=100) == (200, 80)
