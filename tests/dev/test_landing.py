"""Tests for resolving where a resize drag lands."""

from __future__ import annotations

from typing import Any

from nuiitivet.dev import landing
from nuiitivet.dev.source_edit import SNAP_BAND
from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.testing import mount
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.text import TextBase as Text


class _Square(Widget):
    def __init__(self, size: int = 24) -> None:
        super().__init__(width=size, height=size)


class _Bare(Widget):
    def __init__(self) -> None:
        super().__init__()


class _Card(ComposableWidget):
    def build(self) -> Any:
        return Text("AAA", width=100, height=40)


# --- which axes ---------------------------------------------------------------


def test_a_size_parameter_couples_both_axes_to_one_keyword() -> None:
    assert landing.editable_axes(_Square()) == {"width": "size", "height": "size"}


def test_width_and_height_parameters_are_editable() -> None:
    assert landing.editable_axes(Text("AAA")) == {"width": "width", "height": "height"}


def test_a_constructor_with_neither_is_not_resizable() -> None:
    assert landing.editable_axes(_Bare()) == {}


# --- what is declared ---------------------------------------------------------


def test_declared_reads_the_three_spellings_and_nothing_else() -> None:
    assert landing.declared(Text("A", width=180), "width") == 180
    assert landing.declared(Text("A", width="auto"), "width") == "auto"
    assert landing.declared(Text("A", width="wt"), "width") == "wt"
    assert landing.declared(Text("A", width="wt2"), "width") is None


# --- the intrinsic size -------------------------------------------------------


def test_the_intrinsic_size_ignores_a_fixed_sizing_and_restores_it() -> None:
    leaf = Text("AAA", width=300, height=300)
    with mount(Column(children=[leaf])) as host:
        host.layout(400, 400)

        width, height = landing.intrinsic_size(leaf)

        assert 0 < width < 300 and 0 < height < 300
        assert leaf.width_sizing == Sizing.fixed(300)
        assert leaf.height_sizing == Sizing.fixed(300)
        assert leaf.preferred_size()[0] == 300, "the fixed reading must not have leaked"


# --- the weight target --------------------------------------------------------


def test_a_columns_cross_axis_weight_fills_its_content_width() -> None:
    leaf = Text("AAA", width=100)
    with mount(Column(children=[leaf], padding=10)) as host:
        host.layout(300, 200)

        assert landing.weight_target(leaf, "width") == 280


def test_a_columns_main_axis_weight_is_a_share_of_the_leftover() -> None:
    """Fixed siblings take theirs first; the remainder is split with the other weight."""
    leaf = Text("AAA", height=40)
    with mount(Column(children=[Text("top", height=40), leaf, Text("bottom", height="wt")], gap=0)) as host:
        host.layout(300, 200)

        assert landing.weight_target(leaf, "height") == 80


def test_a_rows_main_axis_is_its_width() -> None:
    leaf = Text("AAA", width=40)
    with mount(Row(children=[Text("left", width=100), leaf], gap=0)) as host:
        host.layout(300, 200)

        assert landing.weight_target(leaf, "width") == 200
        assert landing.weight_target(leaf, "height") == 200


def test_a_stack_child_fills_the_stack() -> None:
    leaf = Text("AAA", width=40)
    with mount(Stack(children=[Text("under"), leaf])) as host:
        host.layout(300, 200)

        assert landing.weight_target(leaf, "width") == 300


def test_an_unknown_container_offers_no_weight_target() -> None:
    leaf = Text("AAA", width=40)
    with mount(Flow(children=[leaf])) as host:
        host.layout(300, 200)

        assert landing.weight_target(leaf, "width") is None


def test_a_composable_wrapper_is_transparent() -> None:
    """The built text's container is the column around the composable."""
    card = _Card()
    with mount(Column(children=[card])) as host:
        host.layout(300, 200)
        host.settle()
        leaf = card._built

        container, member = landing.layout_container(leaf)

        assert isinstance(container, Column)
        assert member is card
        assert landing.weight_target(leaf, "width") == 300


# --- resolving ----------------------------------------------------------------


def test_within_the_band_of_the_intrinsic_size_lands_on_auto() -> None:
    assert landing.resolve(63.0, 60, 300) == landing.Landing("auto", 60)


def test_within_the_band_of_the_weight_size_lands_on_wt() -> None:
    assert landing.resolve(296.0, 60, 300) == landing.Landing("wt", 300)


def test_anywhere_else_lands_on_the_rounded_int() -> None:
    assert landing.resolve(180.4, 60, 300) == landing.Landing(180, 180)


def test_the_band_edge_is_inclusive_and_snapping_can_be_off() -> None:
    assert landing.resolve(60 + SNAP_BAND, 60, None).value == "auto"
    assert landing.resolve(60 + SNAP_BAND + 0.6, 60, None).value == 60 + int(SNAP_BAND) + 1
    assert landing.resolve(61.0, 60, 300, snap=False) == landing.Landing(61, 61)


def test_auto_wins_when_both_bands_cover_the_point() -> None:
    assert landing.resolve(62.0, 60, 64).value == "auto"
