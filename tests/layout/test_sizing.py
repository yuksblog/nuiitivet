import pytest
from nuiitivet.rendering.sizing import (
    Sizing,
    clear_sizing_cache,
    enable_sizing_cache_profiling,
    get_sizing_cache_stats,
    parse_sizing,
    reset_sizing_cache_stats,
)
from nuiitivet.layout.spacer import Spacer


def test_parse_sizing_numeric_fixed():
    dim = parse_sizing(24)
    assert dim.kind == "fixed"
    assert dim.value == 24


def test_parse_sizing_auto_string():
    dim = parse_sizing("auto")
    assert dim.kind == "auto"


def test_parse_sizing_weight_string():
    dim = parse_sizing("wt25")
    assert dim.kind == "weight"
    assert dim.value == 25


def test_parse_sizing_bare_wt_is_weight_one():
    for spec in ("wt", "wt1", " WT "):
        dim = parse_sizing(spec)
        assert dim.kind == "weight"
        assert dim.value == 1


def test_parse_sizing_weight_is_case_insensitive():
    dim = parse_sizing("WT2")
    assert dim.kind == "weight"
    assert dim.value == 2


def test_parse_sizing_fractional_weight():
    dim = parse_sizing("wt0.5")
    assert dim.kind == "weight"
    assert dim.value == 0.5


def test_sizing_weight_of_zero_degrades_to_auto():
    assert Sizing.weight(0) == Sizing.auto()


@pytest.mark.parametrize("spec", ["wt0", "wt-1", "wtnan", "wtinf"])
def test_parse_sizing_rejects_non_positive_weight(spec):
    with pytest.raises(ValueError):
        parse_sizing(spec)


@pytest.mark.parametrize("spec", ["50%", "100%", "1%"])
def test_parse_sizing_rejects_the_removed_percentage_spelling(spec):
    """Percentages were never fractions of the parent; the spelling is gone."""

    with pytest.raises(ValueError):
        parse_sizing(spec)


@pytest.mark.parametrize("spec", ["bogus", "wtx", "flex", "weight"])
def test_parse_sizing_invalid_string(spec):
    with pytest.raises(ValueError):
        parse_sizing(spec)


def test_spacer_accepts_sizing_strings():
    spacer = Spacer(width="auto", height="wt50")
    assert spacer.width_sizing.kind == "auto"
    assert spacer.height_sizing.kind == "weight"
    assert spacer.height_sizing.value == 50
    assert spacer.preferred_size() == (0, 0)

    weight_spacer = Spacer(width=Sizing.weight(1), height=Sizing.weight(1))
    assert weight_spacer.width_sizing.kind == "weight"
    assert weight_spacer.height_sizing.kind == "weight"
    assert weight_spacer.preferred_size() == (0, 0)


def test_spacer_fixed_preferred_size():
    spacer = Spacer(width=10, height=4)
    w, h = spacer.preferred_size()
    assert w == 10
    assert h == 4


def test_sizing_parse_cache_stats():
    enable_sizing_cache_profiling(True)
    reset_sizing_cache_stats()
    clear_sizing_cache()
    try:
        parse_sizing("wt40")
        parse_sizing("wt40")
        stats = get_sizing_cache_stats()
        assert stats["parse_hits"] >= 1
        assert stats["parse_misses"] >= 1
    finally:
        reset_sizing_cache_stats()
        enable_sizing_cache_profiling(False)
        clear_sizing_cache()
