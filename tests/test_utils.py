from nuiitivet.layout.metrics import align_offset, compute_prefix_offsets, distribute_space


def test_compute_prefix_offsets_basic():
    sizes = [10, 20, 15]
    offsets = compute_prefix_offsets(sizes, 2)
    assert offsets == [0, 12, 34]


def test_compute_prefix_offsets_empty_and_zero():
    assert compute_prefix_offsets([], 3) == []
    assert compute_prefix_offsets([0, -5, 3], 1) == [0, 1, 2]


def test_distribute_space_all_zero_prefs():
    alloc = distribute_space([0, 0, 0], total=30, spacing=2)
    assert alloc == [9, 9, 8]


def test_distribute_space_proportional_and_round_robin():
    prefs = [1, 1, 2]
    alloc = distribute_space(prefs, total=40, spacing=1)
    assert alloc == [10, 9, 19]


def test_distribute_space_leftover_round_robin_multiple():
    prefs = [1, 0, 0]
    alloc = distribute_space(prefs, total=10, spacing=0)
    assert alloc[0] >= alloc[1]


def test_align_offset_variants():
    assert align_offset(10, 4, "start") == 0
    assert align_offset(10, 4, "center") == 3
    assert align_offset(10, 4, "end") == 6
    assert align_offset(3, 5, "center") == 0
    assert align_offset(-5, 3, "center") == 0
