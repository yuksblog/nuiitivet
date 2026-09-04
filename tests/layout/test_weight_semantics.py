"""A weight is a share of the leftover space, never a fraction of the parent.

These tests pin the single framework-wide interpretation
across a layout container and an overlay: a lone
weight child fills the available extent whatever its weight, and several weight
siblings split the extent in proportion to their weights.
"""

from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.overlay.overlay_position import OverlayPosition


def _positioned(child: Container, width: int, height: int) -> None:
    content = OverlayPosition.aligned("center").make_position_content(child)
    content.layout(width, height)


def test_lone_weight_child_fills_the_row_whatever_its_weight():
    half = Container(width="wt50", height=10)
    row = Row(children=[half], width=800, height=600)
    row.layout(800, 600)

    assert half.layout_rect == (0, 0, 800, 10)


def test_weight_siblings_split_the_row_by_weight():
    left = Container(width="wt50", height=10)
    right = Container(width="wt150", height=10)
    row = Row(children=[left, right], width=800, height=600)
    row.layout(800, 600)

    assert left.layout_rect[2] == 200
    assert right.layout_rect[2] == 600


def test_lone_weight_child_fills_the_overlay_whatever_its_weight():
    child = Container(width="wt50", height="wt50")
    _positioned(child, 800, 600)

    assert child.layout_rect == (0, 0, 800, 600)


def test_overlay_and_row_agree_on_the_same_weight_spec():
    in_row = Container(width="wt25", height=10)
    row = Row(children=[in_row], width=800, height=600)
    row.layout(800, 600)

    in_overlay = Container(width="wt25", height=10)
    _positioned(in_overlay, 800, 600)

    assert in_row.layout_rect[2] == in_overlay.layout_rect[2] == 800


def test_weight_does_not_normalize_against_a_fixed_sibling():
    """`wt50` next to a fixed child takes the whole remainder, not half the row."""

    fixed = Container(width=100, height=10)
    weighted = Container(width="wt50", height=10)
    row = Row(children=[fixed, weighted], width=800, height=600)
    row.layout(800, 600)

    assert weighted.layout_rect[2] == 700
