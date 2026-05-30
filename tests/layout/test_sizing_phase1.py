"""Test Phase 1: Sizing behavior with non-shrinking fixed/auto elements."""

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.container import Container
from nuiitivet.rendering.sizing import Sizing


def test_fixed_auto_do_not_shrink_in_column():
    """fixed and auto elements should not shrink even if space is insufficient."""
    col = Column(
        [
            Container(height=Sizing.fixed(50)),
            Container(height=Sizing.auto()),
            Container(height=Sizing.fixed(30)),
        ],
        gap=10,
        padding=0,
    )
    pref_w, pref_h = col.preferred_size()
    assert pref_h == 100
    base_sizes = [50, 0, 30]
    flex_weights = [0, 0, 0]
    usable = 80 - 20
    alloc = Column._allocate_main_sizes(base_sizes, flex_weights, usable)
    assert alloc == [50, 0, 30]


def test_stretch_shrinks_to_zero_if_needed():
    """flex elements should shrink to 0 if space is very limited."""
    _ = Column(
        [
            Container(height=Sizing.fixed(40)),
            Container(height=Sizing.flex()),
            Container(height=Sizing.fixed(40)),
        ],
        gap=10,
        padding=0,
    )
    base_sizes = [40, 0, 40]
    flex_weights = [0, 1.0, 0]
    usable = 100 - 20
    alloc = Column._allocate_main_sizes(base_sizes, flex_weights, usable)
    assert alloc == [40, 0, 40]


def test_stretch_weight_distribution():
    """flex elements with different weights should share space proportionally."""
    _ = Column(
        [
            Container(height=Sizing.flex(1)),
            Container(height=Sizing.flex(2)),
            Container(height=Sizing.flex(1)),
        ],
        gap=0,
        padding=0,
    )
    base_sizes = [0, 0, 0]
    flex_weights = [1.0, 2.0, 1.0]
    usable = 100
    alloc = Column._allocate_main_sizes(base_sizes, flex_weights, usable)
    assert alloc[0] == 25
    assert alloc[1] == 50
    assert alloc[2] == 25


def test_mixed_fixed_auto_stretch():
    """Mix of fixed, auto, and flex should work correctly."""
    _ = Column(
        [
            Container(height=Sizing.fixed(30)),
            Container(height=Sizing.auto()),
            Container(height=Sizing.flex()),
        ],
        gap=5,
        padding=10,
    )
    base_sizes = [30, 0, 0]
    flex_weights = [0, 0, 1.0]
    usable = 120
    alloc = Column._allocate_main_sizes(base_sizes, flex_weights, usable)
    assert alloc[0] == 30
    assert alloc[1] == 0
    assert alloc[2] == 90


def test_padding_and_spacing_are_guaranteed():
    """padding and spacing should be guaranteed even with overflow."""
    col = Column(
        [Container(height=Sizing.fixed(50)), Container(height=Sizing.fixed(50))],
        gap=20,
        padding=15,
    )
    pref_w, pref_h = col.preferred_size()
    assert pref_h == 150


def test_row_fixed_auto_do_not_shrink():
    """Same behavior for Row (horizontal axis)."""
    _ = Row(
        [
            Container(width=Sizing.fixed(50)),
            Container(width=Sizing.auto()),
            Container(width=Sizing.fixed(30)),
        ],
        gap=10,
        padding=0,
    )
    base_sizes = [50, 0, 30]
    flex_weights = [0, 0, 0]
    usable = 60
    alloc = Row._allocate_main_sizes(base_sizes, flex_weights, usable)
    assert alloc == [50, 0, 30]


def test_stretch_only_no_overflow():
    """If only flex elements, no overflow should occur."""
    _ = Column(
        [
            Container(height=Sizing.flex()),
            Container(height=Sizing.flex()),
            Container(height=Sizing.flex()),
        ],
        gap=10,
        padding=10,
    )
    base_sizes = [0, 0, 0]
    flex_weights = [1.0, 1.0, 1.0]
    usable = 60
    alloc = Column._allocate_main_sizes(base_sizes, flex_weights, usable)
    assert alloc[0] == 20
    assert alloc[1] == 20
    assert alloc[2] == 20


def test_zero_weight_stretch_behaves_like_auto():
    """Sizing.flex(0) should be treated as auto (edge case)."""
    dim = Sizing.flex(0)
    assert dim.kind == "auto"


def test_negative_remaining_space():
    """When fixed/auto require more than available, remaining is negative."""
    _ = Column(
        [Container(height=Sizing.fixed(60)), Container(height=Sizing.fixed(60))],
        gap=10,
        padding=0,
    )
    base_sizes = [60, 60]
    flex_weights = [0, 0]
    usable = 90
    alloc = Column._allocate_main_sizes(base_sizes, flex_weights, usable)
    assert alloc == [60, 60]
