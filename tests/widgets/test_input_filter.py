"""Input filters.

A filter runs between a keystroke and the field's value. The character-level
filters know which characters they dropped and move the caret exactly; the
``str -> str`` shorthand only sees the resulting string, so its caret follows
the length change.
"""

import pytest

from nuiitivet.widgets.input_filter import (
    InputFilter,
    allow,
    deny,
    digits_only,
    matching,
    max_length,
    to_input_filter,
)
from nuiitivet.widgets.text_editing import TextEditingValue, TextRange


def _value(text: str, caret: int | None = None) -> TextEditingValue:
    pos = len(text) if caret is None else caret
    return TextEditingValue(text=text, selection=TextRange(pos, pos))


def _apply(f: InputFilter, old: str, new: str, caret: int | None = None) -> TextEditingValue:
    return f.apply(_value(old), _value(new, caret))


def test_digits_only_drops_non_digits():
    assert _apply(digits_only(), "12", "12a").text == "12"


def test_digits_only_keeps_the_caret_before_the_dropped_characters():
    # "1a2b3" with the caret after "b"; two characters before it are dropped.
    result = _apply(digits_only(), "", "1a2b3", caret=4)
    assert result.text == "123"
    assert result.selection == TextRange(2, 2)


def test_allow_is_matched_one_character_at_a_time():
    assert _apply(allow(r"[A-Za-z ]"), "", "ab1 c2").text == "ab c"


def test_deny_is_the_inverse_of_allow():
    assert _apply(deny(r"\s"), "", "a b\tc").text == "abc"


def test_a_filter_that_drops_nothing_returns_the_value_unchanged():
    value = _value("123")
    assert digits_only().apply(_value(""), value) is value


def test_max_length_truncates_from_the_end():
    result = _apply(max_length(3), "abc", "abcd")
    assert result.text == "abc"
    assert result.selection == TextRange(3, 3)


def test_max_length_leaves_shorter_text_alone():
    assert _apply(max_length(5), "ab", "abc").text == "abc"


def test_max_length_rejects_a_negative_limit():
    with pytest.raises(ValueError):
        max_length(-1)


def test_matching_rejects_the_whole_edit():
    """A whole-string rule has no partial result to keep, so it reverts."""
    decimal = matching(r"[0-9]*\.?[0-9]*")
    assert _apply(decimal, "1.5", "1.5.").text == "1.5"


def test_matching_accepts_an_incomplete_but_typeable_value():
    # "1." is not a valid decimal, but it has to be typeable to reach "1.5".
    decimal = matching(r"[0-9]*\.?[0-9]*")
    assert _apply(decimal, "1", "1.").text == "1."


def test_matching_reverts_to_the_previous_caret_as_well():
    result = matching(r"[0-9]*").apply(_value("12", caret=1), _value("12a", caret=2))
    assert result.text == "12"
    assert result.selection == TextRange(1, 1)


def test_a_callable_is_accepted_as_a_filter():
    assert _apply(to_input_filter(lambda s: s.upper()), "ab", "abc").text == "ABC"


def test_a_same_length_callable_leaves_the_caret_alone():
    result = to_input_filter(lambda s: s.upper()).apply(_value("ab"), _value("abc", caret=1))
    assert result.text == "ABC"
    assert result.selection == TextRange(1, 1)


def test_a_shortening_callable_moves_the_caret_by_the_length_delta():
    result = to_input_filter(lambda s: s.replace(" ", "")).apply(_value(""), _value("a b c", caret=5))
    assert result.text == "abc"
    assert result.selection == TextRange(3, 3)


def test_a_raising_callable_leaves_the_edit_untouched():
    def boom(_text: str) -> str:
        raise RuntimeError("nope")

    assert _apply(to_input_filter(boom), "ab", "abc").text == "abc"


def test_filters_compose_left_to_right():
    result = _apply(digits_only() | max_length(3), "", "1a2b3c4")
    assert result.text == "123"


def test_composition_order_is_observed():
    # Truncating first leaves "1a2", which then filters down to "12".
    assert _apply(max_length(3) | digits_only(), "", "1a2b3c4").text == "12"


def test_a_callable_composes_on_either_side():
    assert _apply(digits_only() | (lambda s: s + "!"), "", "1a2").text == "12!"
    assert _apply((lambda s: s.strip()) | max_length(2), "", "  abc  ").text == "ab"


def test_chained_filters_flatten():
    chained = digits_only() | max_length(4) | (lambda s: s)
    assert _apply(chained, "", "1a2b3c4d5").text == "1234"
