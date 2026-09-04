"""A ComposableWidget is transparent to layout metadata.

A value declared on the wrapper wins; an undeclared one is derived from the
widget its build() returned. The regression shape is the one from the bug
report: Card -> ComposableWidget -> Column(height="wt") must fill exactly as
Card -> Column(height="wt") does, instead of collapsing to intrinsic size.
"""

from nuiitivet.layout.column import Column
from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.row import Row
from nuiitivet.layout.spacer import Spacer
from nuiitivet.material.card import Card
from nuiitivet.material.text import Text
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.testing import mount
from nuiitivet.widgeting.widget import ComposableWidget, Widget


def _fill_column() -> Column:
    return Column(
        [Text("top"), Spacer(height="wt"), Text("bottom")],
        width="wt",
        height="wt",
    )


class _Inner(ComposableWidget):
    """The wrapper under test: builds a weight-sized Column, declares nothing."""

    def build(self) -> Widget:
        return _fill_column()


class _DeclaredInner(ComposableWidget):
    def __init__(self, *, width: SizingLike = None, height: SizingLike = None) -> None:
        super().__init__(width=width, height=height)

    def build(self) -> Widget:
        return _fill_column()


def test_weight_fills_through_an_intervening_composable():
    inner = _Inner()
    card = Card(inner, width="wt", height="wt")
    with mount(card) as host:
        host.layout(400, 400)

        column = inner.built_child
        assert isinstance(column, Column)
        assert inner.layout_rect is not None and inner.layout_rect[2:] == column.layout_rect[2:]
        # The spacer received the leftover height: the texts sit at both ends.
        top, spacer, bottom = column.children
        assert spacer.layout_rect[3] > 0
        assert bottom.layout_rect[1] + bottom.layout_rect[3] == column.layout_rect[1] + column.layout_rect[3]


def test_composable_matches_the_column_it_builds():
    """The wrapper must be layout-invisible: same result as the bare Column."""
    inner = _Inner()
    with mount(Card(inner, width="wt", height="wt")) as host:
        host.layout(400, 400)
        wrapped_rects = [tuple(c.layout_rect) for c in inner.built_child.children]

    bare = _fill_column()
    with mount(Card(bare, width="wt", height="wt")) as host:
        host.layout(400, 400)
        bare_rects = [tuple(c.layout_rect) for c in bare.children]

    assert wrapped_rects == bare_rects


def test_declared_sizing_on_the_wrapper_wins():
    inner = _DeclaredInner(width=120, height=90)
    row = Row([inner], width="wt", height="wt")
    with mount(row) as host:
        host.layout(400, 400)

        # The parent allocates the declared size, and the "wt" child fills it.
        assert inner.layout_rect[2:] == (120, 90)
        assert inner.built_child.layout_rect[2:] == (120, 90)


def test_explicit_auto_is_a_declaration_not_an_omission():
    """`"auto"` pins the intrinsic size — the opt-out from derivation."""
    inner = _DeclaredInner(width="auto", height="auto")
    with mount(Card(inner, width="wt", height="wt")) as host:
        host.layout(400, 400)

        assert inner.width_sizing.kind == "auto"
        assert inner.height_sizing.kind == "auto"
        # Laid out at intrinsic size, not the card's full extent.
        assert inner.layout_rect[3] < 400


def test_before_build_the_wrapper_reports_its_own_default():
    inner = _Inner()
    assert inner.built_child is None
    assert inner.width_sizing.kind == "auto"
    assert inner.height_sizing.kind == "auto"


def test_derived_sizing_follows_a_rebuild():
    class Switching(ComposableWidget):
        def __init__(self) -> None:
            super().__init__()
            self.wide = False

        def build(self) -> Widget:
            return Column([Text("x")], width="wt" if self.wide else 50)

    widget = Switching()
    with mount(widget):
        assert widget.width_sizing.kind == "fixed"

        widget.wide = True
        widget.rebuild()
        assert widget.width_sizing.kind == "weight"


def test_cross_align_derives_from_the_built_child():
    class Centered(ComposableWidget):
        def build(self) -> Widget:
            return CrossAligned(Text("centered", width=50), "center")

    plain = Text("plain", width=50)
    composed = Centered()
    column = Column([plain, composed], width=400, height="wt")
    with mount(column) as host:
        host.layout(400, 200)

        assert composed.cross_align == "center"
        # The column honoured the derived hint: the composed row is centered
        # while the plain one keeps the default (start) position.
        assert plain.layout_rect[0] == 0
        assert composed.layout_rect[0] > 0


def test_declared_cross_align_on_the_wrapper_wins():
    class Centered(ComposableWidget):
        def build(self) -> Widget:
            return CrossAligned(Text("centered", width=50), "center")

    composed = Centered()
    composed.cross_align = "end"
    with mount(composed):
        assert composed.cross_align == "end"


def test_layout_align_derives_from_the_built_child():
    class Aligned(ComposableWidget):
        def build(self) -> Widget:
            child: Widget = Text("x")
            child.layout_align = "center"
            return child

    composed = Aligned()
    with mount(composed):
        assert composed.layout_align == "center"
