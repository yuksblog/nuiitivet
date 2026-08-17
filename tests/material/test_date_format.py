"""Tests for DateFormat and the default date helpers."""

from datetime import date

import pytest

from nuiitivet.material.date_format import (
    DEFAULT_DATE_FORMAT,
    DateFormat,
    format_date,
    is_date,
    parse_date,
)
from nuiitivet.observable import Observable

# ---------------------------------------------------------------------------
# Pattern compilation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pattern,text,expected",
    [
        ("mm/dd/yyyy", "06/10/2026", date(2026, 6, 10)),
        ("dd.mm.yyyy", "10.06.2026", date(2026, 6, 10)),
        ("yyyy-mm-dd", "2026-06-10", date(2026, 6, 10)),
        ("mm/dd/yy", "06/10/26", date(2026, 6, 10)),
        ("dd mm yyyy", "10 06 2026", date(2026, 6, 10)),
        ("yyyy年mm月dd日", "2026年06月10日", date(2026, 6, 10)),
    ],
)
def test_pattern_round_trips(pattern, text, expected):
    """Each pattern reads its own rendering back unchanged."""
    fmt = DateFormat(pattern)
    assert fmt.parse(text) == expected
    assert fmt.format(expected) == text
    assert fmt.parse(fmt.format(expected)) == expected


def test_yyyy_wins_over_yy():
    """The longer token is matched first, so 'yyyy' is not read as 'yy' + 'yy'."""
    assert DateFormat("yyyy-mm-dd").parse("2026-06-10") == date(2026, 6, 10)
    # If 'yyyy' were split, a 4-digit year would not parse at all.
    assert DateFormat("yyyy-mm-dd").format(date(2026, 6, 10)) == "2026-06-10"


def test_non_token_characters_are_literals():
    """Punctuation and digits carry through untouched."""
    fmt = DateFormat("[dd/mm/yyyy]")
    assert fmt.format(date(2026, 6, 10)) == "[10/06/2026]"
    assert fmt.parse("[10/06/2026]") == date(2026, 6, 10)


def test_percent_is_escaped():
    """A literal '%' does not turn into a strftime directive."""
    fmt = DateFormat("dd%mm%yyyy")
    assert fmt.format(date(2026, 6, 10)) == "10%06%2026"
    assert fmt.parse("10%06%2026") == date(2026, 6, 10)


# ---------------------------------------------------------------------------
# Pattern validation
# ---------------------------------------------------------------------------


def test_unknown_ascii_letters_are_rejected():
    """A stray ASCII letter is a mistyped token, not a literal: accepting it
    would produce a format that never parses anything."""
    with pytest.raises(ValueError, match="not part of a token"):
        DateFormat("mmm/dd/yyyy")


@pytest.mark.parametrize(
    "pattern,text",
    [
        ("yyyy年mm月dd日", "2026年06月10日"),
        ("dd·mm·yyyy", "10·06·2026"),
        ("dd.mm.yyyyг", "10.06.2026г"),
    ],
)
def test_non_ascii_characters_are_literals(pattern, text):
    """Only ASCII letters can be confused with a token, so only they are refused.

    Without this a Japanese pattern is inexpressible, though ``strftime`` has
    always been able to render one.
    """
    fmt = DateFormat(pattern)
    assert fmt.format(date(2026, 6, 10)) == text
    assert fmt.parse(text) == date(2026, 6, 10)


def test_uppercase_tokens_are_rejected():
    """Case is reserved: 'mm' vs 'MM' will be minutes vs months for a time format."""
    with pytest.raises(ValueError, match="not part of a token"):
        DateFormat("MM/DD/YYYY")


def test_repeated_field_is_rejected():
    """Naming the same field twice cannot round-trip."""
    with pytest.raises(ValueError, match="names the year twice"):
        DateFormat("yyyy-mm-dd-yy")


def test_missing_field_is_rejected():
    """A date needs all three fields; without a year strptime would invent 1900."""
    with pytest.raises(ValueError, match="does not name the year"):
        DateFormat("mm/dd")


def test_also_accepts_is_validated_too():
    """A malformed alternative fails at construction, not at the first parse."""
    with pytest.raises(ValueError, match="not part of a token"):
        DateFormat("mm/dd/yyyy", also_accepts=("mmm/dd/yyyy",))


# ---------------------------------------------------------------------------
# Parsing behaviour
# ---------------------------------------------------------------------------


def test_also_accepts_is_tried_in_order_and_never_emitted():
    """Input is lenient, output is not."""
    fmt = DateFormat("mm/dd/yyyy", also_accepts=("yyyy-mm-dd",))
    assert fmt.parse("06/10/2026") == date(2026, 6, 10)
    assert fmt.parse("2026-06-10") == date(2026, 6, 10)
    assert fmt.format(date(2026, 6, 10)) == "06/10/2026"


def test_parse_ignores_surrounding_whitespace():
    assert DateFormat("mm/dd/yyyy").parse("  06/10/2026 ") == date(2026, 6, 10)


def test_parse_returns_none_for_unreadable_text():
    """Empty and half-typed text are not dates -- the normal state of a field
    someone is typing into."""
    fmt = DateFormat("mm/dd/yyyy")
    assert fmt.parse("") is None
    assert fmt.parse("06/1") is None
    assert fmt.parse("not-a-date") is None
    assert fmt.parse("13/40/2026") is None
    assert fmt.parse("2026-06-10") is None  # not accepted by this format


def test_format_of_none_is_empty():
    assert DateFormat("mm/dd/yyyy").format(None) == ""


def test_matches_is_the_predicate_form_of_parse():
    fmt = DateFormat("mm/dd/yyyy")
    assert fmt.matches("06/10/2026") is True
    assert fmt.matches("06/1") is False
    assert fmt.matches("") is False


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_str_is_the_pattern_so_it_can_be_shown_as_a_hint():
    assert str(DateFormat("dd.mm.yyyy")) == "dd.mm.yyyy"
    assert DateFormat("dd.mm.yyyy").pattern == "dd.mm.yyyy"


def test_repr_round_trips():
    assert repr(DateFormat("mm/dd/yyyy")) == "DateFormat('mm/dd/yyyy')"
    assert repr(DateFormat("mm/dd/yyyy", also_accepts=("yyyy-mm-dd",))) == (
        "DateFormat('mm/dd/yyyy', also_accepts=('yyyy-mm-dd',))"
    )


def test_equality_covers_the_accepted_patterns():
    assert DateFormat("mm/dd/yyyy") == DateFormat("mm/dd/yyyy")
    assert DateFormat("mm/dd/yyyy") != DateFormat("dd/mm/yyyy")
    assert DateFormat("mm/dd/yyyy") != DateFormat("mm/dd/yyyy", also_accepts=("yyyy-mm-dd",))
    assert DateFormat("mm/dd/yyyy") != "mm/dd/yyyy"
    assert hash(DateFormat("mm/dd/yyyy")) == hash(DateFormat("mm/dd/yyyy"))


# ---------------------------------------------------------------------------
# The default format and its function forms
# ---------------------------------------------------------------------------


def test_default_accepts_three_patterns_and_emits_one():
    """The leniency that was there before DateFormat existed is preserved."""
    assert parse_date("06/10/2026") == date(2026, 6, 10)
    assert parse_date("06-10-2026") == date(2026, 6, 10)
    assert parse_date("2026-06-10") == date(2026, 6, 10)
    assert format_date(date(2026, 6, 10)) == "06/10/2026"


def test_default_pattern_is_the_hint_text():
    assert DEFAULT_DATE_FORMAT.pattern == "mm/dd/yyyy"


def test_module_functions_delegate_to_the_default_format():
    assert parse_date("06/10/2026") == DEFAULT_DATE_FORMAT.parse("06/10/2026")
    assert format_date(date(2026, 6, 10)) == DEFAULT_DATE_FORMAT.format(date(2026, 6, 10))
    assert is_date("06/10/2026") == DEFAULT_DATE_FORMAT.matches("06/10/2026")


def test_parse_date_invalid_returns_none():
    assert parse_date("not-a-date") is None
    assert parse_date("") is None
    assert parse_date("13/40/2026") is None


def test_format_date_of_none_is_empty():
    assert format_date(None) == ""


# ---------------------------------------------------------------------------
# The idiom these exist for
# ---------------------------------------------------------------------------


def test_derived_date_holds_the_last_valid_value():
    """Text is the cell, the date is derived: filter() keeps the last good one."""
    text: Observable[str] = Observable("")
    derived = text.filter(is_date, initial="").map(parse_date)

    # The seed is text, so it goes through map as well.
    assert derived.value is None

    text.value = "06/10/2026"
    assert derived.value == date(2026, 6, 10)

    # Half-typed input is rejected by the filter, so the last valid date stands
    # and the text itself is left exactly as the user typed it.
    text.value = "06/1"
    assert derived.value == date(2026, 6, 10)
    assert text.value == "06/1"

    # The other spelling reports the invalid state instead of hiding it.
    reported = text.map(parse_date)
    assert reported.value is None


def test_a_custom_format_derives_with_its_own_bound_methods():
    """The point of the object: one source for the widget and the derivation."""
    fmt = DateFormat("dd.mm.yyyy")
    text: Observable[str] = Observable("")
    derived = text.map(fmt.parse)

    text.value = "10.06.2026"
    assert derived.value == date(2026, 6, 10)

    # What the widget writes back is what the derivation reads.
    text.value = fmt.format(date(2026, 7, 4))
    assert derived.value == date(2026, 7, 4)
