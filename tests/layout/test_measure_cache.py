"""Regression tests for the preferred_size measure cache.

Every layout pass used to re-measure the entire subtree — text shaping
included — so a width animation cost O(total children) per frame. These tests
pin the fix: an unchanged subtree under unchanged (or compatibly shrunk)
constraints is not re-measured, and every invalidation route drops the cache.
"""

import math
from typing import Optional, Tuple

from nuiitivet.layout.column import Column
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.layout.layout_utils import layout_child_if_needed
from nuiitivet.widgeting.widget import Widget


class CountingLeaf(Widget):
    """Leaf with greedy-wrap measurement semantics that counts calls.

    Mimics Text: unconstrained it reports its natural width; under a smaller
    ``max_width`` it wraps, clamping width and growing height.
    """

    def __init__(self, natural_w: int = 100, natural_h: int = 20, **kwargs):
        super().__init__(**kwargs)
        self._natural = (natural_w, natural_h)
        self.measure_calls = 0
        self.layout_calls = 0

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        self.measure_calls += 1
        w, h = self._natural
        if max_width is not None and w > max_width > 0:
            lines = math.ceil(w / max_width)
            return (max_width, h * lines)
        return (w, h)

    def layout(self, width: int, height: int) -> None:
        self.layout_calls += 1
        super().layout(width, height)


def test_repeated_measure_same_constraints_is_cached():
    leaf = CountingLeaf()
    assert measure_preferred_size(leaf, max_width=200) == (100, 20)
    assert measure_preferred_size(leaf, max_width=200) == (100, 20)
    assert leaf.measure_calls == 1


def test_shrinking_constraint_reuses_fitting_result():
    leaf = CountingLeaf(natural_w=100)
    measure_preferred_size(leaf, max_width=200)
    # The result (100) fits any constraint in [100, 200]: no re-measure.
    assert measure_preferred_size(leaf, max_width=150) == (100, 20)
    assert measure_preferred_size(leaf, max_width=100) == (100, 20)
    assert leaf.measure_calls == 1
    # Below the measured width the layout genuinely changes (wrapping).
    assert measure_preferred_size(leaf, max_width=90) == (90, 40)
    assert leaf.measure_calls == 2


def test_growing_constraint_re_measures():
    leaf = CountingLeaf(natural_w=100)
    # Wrapped at 50; a larger constraint may un-wrap, so it must re-measure.
    assert measure_preferred_size(leaf, max_width=50) == (50, 40)
    assert measure_preferred_size(leaf, max_width=80) == (80, 40)
    assert leaf.measure_calls == 2


def test_unconstrained_query_not_served_by_constrained_entry():
    leaf = CountingLeaf(natural_w=100)
    assert measure_preferred_size(leaf, max_width=50) == (50, 40)
    assert measure_preferred_size(leaf) == (100, 20)
    assert leaf.measure_calls == 2
    # ... but an unconstrained entry serves any constraint the result fits.
    assert measure_preferred_size(leaf, max_width=150) == (100, 20)
    assert leaf.measure_calls == 2


def test_mark_needs_layout_drops_cache():
    leaf = CountingLeaf()
    measure_preferred_size(leaf, max_width=200)
    leaf.mark_needs_layout()
    measure_preferred_size(leaf, max_width=200)
    assert leaf.measure_calls == 2


def test_layout_param_change_drops_cache():
    leaf = CountingLeaf()
    measure_preferred_size(leaf, max_width=200)
    leaf.padding = 4
    measure_preferred_size(leaf, max_width=200)
    assert leaf.measure_calls == 2


def test_width_animation_does_not_re_measure_static_children():
    """The motivating scenario: a width animation over a static list.

    Once measured at the widest constraint, shrinking and growing the
    container within that range re-measures no child.
    """
    children = [CountingLeaf(natural_w=100) for _ in range(20)]
    col = Column(list(children), gap=8)

    col.layout(300, 1000)
    baseline = [c.measure_calls for c in children]

    for width in list(range(290, 190, -10)) + list(range(200, 301, 10)):
        col.layout(width, 1000)

    assert [c.measure_calls for c in children] == baseline


def test_child_content_change_re_measures_only_after_invalidation():
    children = [CountingLeaf(natural_w=100) for _ in range(5)]
    col = Column(list(children), gap=8)
    col.layout(300, 1000)

    changed = children[2]
    before = changed.measure_calls
    changed.mark_needs_layout()
    col.layout(300, 1000)

    assert changed.measure_calls == before + 1
    # Untouched siblings stay cached.
    assert children[0].measure_calls == 1
    assert children[4].measure_calls == 1


def test_clean_same_size_child_layout_is_skipped():
    children = [CountingLeaf(natural_w=100) for _ in range(5)]
    col = Column(list(children), gap=8)

    col.layout(300, 1000)
    assert all(c.layout_calls == 1 for c in children)

    # Same size, nothing dirtied: the arrange pass skips the recursion.
    col.layout(300, 1000)
    assert all(c.layout_calls == 1 for c in children)

    # A dirtied child is re-laid; clean siblings are still skipped.
    children[1].mark_needs_layout()
    col.layout(300, 1000)
    assert children[1].layout_calls == 2
    assert children[0].layout_calls == 1


def test_layout_child_if_needed_runs_on_size_change():
    leaf = CountingLeaf(natural_w=100)
    layout_child_if_needed(leaf, 100, 20)
    assert leaf.layout_calls == 1
    layout_child_if_needed(leaf, 100, 20)
    assert leaf.layout_calls == 1
    layout_child_if_needed(leaf, 120, 20)
    assert leaf.layout_calls == 2
