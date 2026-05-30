from nuiitivet.layout.layout_engine import (
    LayoutEngine,
    enable_layout_cache_profiling,
    get_layout_cache_stats,
    reset_layout_cache_stats,
)
from nuiitivet.rendering.sizing import Sizing


class DummyOwner:

    def __init__(self, pad=(0, 0, 0, 0), border_width=0, align=("start", "start")):
        self.padding = pad
        self.border_width = border_width
        self._align = align


class DummyChild:

    def __init__(self, pref_w, pref_h, w_dim=None, h_dim=None):
        self._pref = (pref_w, pref_h)
        self.width_sizing = w_dim if w_dim is not None else Sizing.auto()
        self.height_sizing = h_dim if h_dim is not None else Sizing.auto()
        self.layout_align = None
        self._layout_token = 0

    @property
    def layout_cache_token(self) -> int:
        return int(self._layout_token)

    def bump_layout_cache_token(self) -> None:
        self._layout_token += 1

    def preferred_size(self):
        return self._pref


def test_preferred_size_includes_padding_and_border():
    owner = DummyOwner(pad=(2, 3, 4, 5), border_width=1)
    le = LayoutEngine(owner)
    w, h = le.preferred_size(10, 20)
    assert w == 10 + 2 + 4 + 1 * 2
    assert h == 20 + 3 + 5 + 1 * 2


def test_compute_inner_rect_reduces_by_padding_and_border():
    owner = DummyOwner(pad=(5, 6, 7, 8), border_width=2)
    le = LayoutEngine(owner)
    ix, iy, iw, ih = le.compute_inner_rect(0, 0, 100, 50)
    assert ix == 0 + 5 + 2
    assert iy == 0 + 6 + 2
    assert iw == max(0, 100 - (5 + 7) - 2 * 2)
    assert ih == max(0, 50 - (6 + 8) - 2 * 2)


def test_compute_child_placement_alignment_and_clamping():
    owner = DummyOwner(align=("center", "end"))
    le = LayoutEngine(owner)
    cx, cy, cw, ch = le.compute_child_placement(80, 60, 0, 0)
    assert (cx, cy) == (0, 0)
    assert (cw, ch) == (80, 60)
    cx, cy, cw, ch = le.compute_child_placement(80, 60, 40, 20)
    assert cx == 20
    assert cy == 40
    assert cw == 40
    assert ch == 20


def test_resolve_child_geometry_clamps_auto_sizing_to_inner_rect():
    owner = DummyOwner()
    le = LayoutEngine(owner)
    child = DummyChild(pref_w=400, pref_h=20)
    cx, cy, cw, ch = le.resolve_child_geometry(child, 10, 5, 120, 40)
    assert (cx, cy) == (10, 5)
    assert cw == 120  # auto width clamps to available inner width
    assert ch == 20  # height remains preferred because it fits


def test_resolve_child_geometry_allows_fixed_overflow():
    owner = DummyOwner()
    le = LayoutEngine(owner)
    child = DummyChild(pref_w=50, pref_h=10, w_dim=Sizing.fixed(300))
    cx, cy, cw, ch = le.resolve_child_geometry(child, 0, 0, 120, 40)
    assert cx == 0
    assert cw == 300  # fixed width keeps requested size even if it overflows
    assert ch == 10


def test_layout_engine_preferred_cache_profile_counts():
    enable_layout_cache_profiling(True)
    reset_layout_cache_stats()
    owner = DummyOwner(pad=(1, 2, 3, 4), border_width=2)
    le = LayoutEngine(owner)
    try:
        le.preferred_size(20, 10)
        le.preferred_size(20, 10)
        le.invalidate_cache()
        le.preferred_size(20, 10)
        stats = get_layout_cache_stats()
        assert stats["preferred_hits"] >= 1
        assert stats["preferred_misses"] >= 2
    finally:
        reset_layout_cache_stats()
        enable_layout_cache_profiling(False)


def test_layout_engine_child_placement_cache_hits():
    enable_layout_cache_profiling(True)
    reset_layout_cache_stats()
    owner = DummyOwner(align=("center", "center"))
    le = LayoutEngine(owner)
    try:
        le.compute_child_placement(80, 60, 30, 20, clamp_w=True, clamp_h=True)
        le.compute_child_placement(80, 60, 30, 20, clamp_w=True, clamp_h=True)
        stats = get_layout_cache_stats()
        assert stats["placement_hits"] >= 1
        assert stats["placement_misses"] >= 1
    finally:
        reset_layout_cache_stats()
        enable_layout_cache_profiling(False)


def test_child_token_invalidation_causes_cache_miss():
    enable_layout_cache_profiling(True)
    reset_layout_cache_stats()
    owner = DummyOwner()
    le = LayoutEngine(owner)
    child = DummyChild(pref_w=40, pref_h=20)
    try:
        le.resolve_child_geometry(child, 0, 0, 100, 60)
        first_stats = get_layout_cache_stats()
        child.bump_layout_cache_token()
        le.resolve_child_geometry(child, 0, 0, 100, 60)
        stats = get_layout_cache_stats()
        assert stats["placement_misses"] >= first_stats["placement_misses"] + 1
    finally:
        reset_layout_cache_stats()
        enable_layout_cache_profiling(False)
