"""Tests for alignment normalization and the shared alignment→point helper."""

import warnings

import pytest

from nuiitivet.layout.alignment import (
    NINE_POINT_ALIGNMENTS,
    alignment_to_point,
    normalize_alignment,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("top-left", ("start", "start")),
        ("top-center", ("center", "start")),
        ("center", ("center", "center")),
        ("bottom-right", ("end", "end")),
    ],
)
def test_normalize_hyphen_form(value, expected):
    assert normalize_alignment(value, default=("start", "start")) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("top_left", ("start", "start")),
        ("bottom_center", ("center", "end")),
        ("CENTER_RIGHT", ("end", "center")),
    ],
)
def test_normalize_underscore_alias(value, expected):
    """Underscore form (and mixed case) is accepted as an alias."""
    assert normalize_alignment(value, default=("start", "start")) == expected


@pytest.mark.parametrize("value", ["start", "center", "end"])
def test_normalize_single_axis_shorthand_no_warning(value):
    """A bare axis token applies to both axes and does not warn."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert normalize_alignment(value, default=("start", "start")) == (value, value)


def test_normalize_tuple_passthrough():
    assert normalize_alignment(("end", "center"), default=("start", "start")) == ("end", "center")


def test_normalize_none_returns_default():
    assert normalize_alignment(None, default=("center", "center")) == ("center", "center")


def test_normalize_unknown_warns_and_falls_back():
    with pytest.warns(UserWarning, match="Unrecognized alignment"):
        result = normalize_alignment("nope", default=("start", "start"))
    assert result == ("nope", "nope")


def test_nine_point_set_is_hyphenated():
    assert all("_" not in token for token in NINE_POINT_ALIGNMENTS)
    assert len(NINE_POINT_ALIGNMENTS) == 9


@pytest.mark.parametrize(
    "axes,expected",
    [
        (("start", "start"), (0.0, 0.0)),
        (("center", "center"), (50.0, 50.0)),
        (("end", "end"), (100.0, 100.0)),
        (("center", "end"), (50.0, 100.0)),
    ],
)
def test_alignment_to_point(axes, expected):
    assert alignment_to_point(axes, 100, 100) == expected
