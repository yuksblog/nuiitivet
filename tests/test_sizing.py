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


def test_parse_sizing_percent_flex():
    dim = parse_sizing("25%")
    assert dim.kind == "flex"
    assert dim.value == 25


def test_parse_sizing_invalid_string():
    with pytest.raises(ValueError):
        parse_sizing("bogus")


def test_spacer_accepts_sizing_strings():
    spacer = Spacer(width="auto", height="50%")
    assert spacer.width_sizing.kind == "auto"
    assert spacer.height_sizing.kind == "flex"
    assert spacer.height_sizing.value == 50
    assert spacer.preferred_size() == (0, 0)

    flex_spacer = Spacer(width=Sizing.flex(1), height=Sizing.flex(1))
    assert flex_spacer.width_sizing.kind == "flex"
    assert flex_spacer.height_sizing.kind == "flex"
    assert flex_spacer.preferred_size() == (0, 0)


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
        parse_sizing("40%")
        parse_sizing("40%")
        stats = get_sizing_cache_stats()
        assert stats["parse_hits"] >= 1
        assert stats["parse_misses"] >= 1
    finally:
        reset_sizing_cache_stats()
        enable_sizing_cache_profiling(False)
        clear_sizing_cache()
