from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget


class MockWidget(Widget):
    def __init__(self, w: int = 10, h: int = 10, **kwargs):
        super().__init__(width=Sizing.fixed(w), height=Sizing.fixed(h), **kwargs)

    def paint(self, canvas, x, y, width, height):
        self.set_last_rect(x, y, width, height)


def test_column_cross_aligned():
    # Column width 100, cross_alignment="start"
    # Child 1: 10x10, no override -> x=0
    # Child 2: 10x10, alignment override "end" -> x=90
    # Child 3: 10x10, alignment override "center" -> x=45

    c1 = MockWidget(10, 10)
    c2_wrapped = CrossAligned(MockWidget(10, 10), "end")
    c3_wrapped = CrossAligned(MockWidget(10, 10), "center")

    col = Column(
        children=[c1, c2_wrapped, c3_wrapped],
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
        cross_alignment="start",
    )

    col.paint(None, 0, 0, 100, 100)

    assert c1.last_rect is not None
    assert c1.last_rect[0] == 0

    assert c2_wrapped.last_rect is not None
    assert c2_wrapped.last_rect[0] == 90

    assert c3_wrapped.last_rect is not None
    assert c3_wrapped.last_rect[0] == 45


def test_row_cross_aligned():
    # Row height 100, cross_alignment="start"
    # Child 1: 10x10, no override -> y=0
    # Child 2: 10x10, alignment override "end" -> y=90

    c1 = MockWidget(10, 10)
    c2_wrapped = CrossAligned(MockWidget(10, 10), "end")

    row = Row(
        children=[c1, c2_wrapped],
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
        cross_alignment="start",
    )

    row.paint(None, 0, 0, 100, 100)

    assert c1.last_rect is not None
    assert c1.last_rect[1] == 0

    assert c2_wrapped.last_rect is not None
    assert c2_wrapped.last_rect[1] == 90


def test_aligned_preserves_override_through_modifiers():
    from nuiitivet.modifiers import background
    from nuiitivet.widgets.box import ModifierBox

    w = MockWidget(10, 10)
    aligned = CrossAligned(w, "end")
    wrapped = aligned.modifier(background("red"))

    assert isinstance(wrapped, ModifierBox)
    assert wrapped.cross_align == "end"
