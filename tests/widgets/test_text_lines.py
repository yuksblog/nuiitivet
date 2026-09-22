"""Tests for the line layout ``EditableText`` and the dev runner's inline field share."""

from __future__ import annotations

from nuiitivet.widgets.text_editing import TextEditingValue, TextRange
from nuiitivet.widgets.text_lines import break_lines, caret_x, index_at, line_edge, line_of, move_lines


def measure(s: str) -> float:
    """Ten units per character."""
    return 10.0 * len(s)


def _at(text: str, caret: int) -> TextEditingValue:
    return TextEditingValue(text, TextRange(caret, caret))


# --- breaking ---------------------------------------------------------------------


def test_an_empty_text_is_one_empty_line() -> None:
    assert break_lines("", measure, 50) == [TextRange(0, 0)]


def test_a_hard_break_ends_the_line_before_it() -> None:
    assert break_lines("ab\n\ncd", measure) == [TextRange(0, 2), TextRange(3, 3), TextRange(4, 6)]


def test_without_a_width_nothing_wraps() -> None:
    assert break_lines("a long line", measure, None) == [TextRange(0, 11)]


def test_a_soft_break_lands_after_the_last_space_that_fits() -> None:
    assert break_lines("hello world foo", measure, 60) == [TextRange(0, 6), TextRange(6, 12), TextRange(12, 15)]


def test_a_space_hangs_past_the_edge_rather_than_opening_a_line() -> None:
    assert break_lines("hello world", measure, 50) == [TextRange(0, 6), TextRange(6, 11)]


def test_a_run_with_no_space_breaks_at_the_character() -> None:
    assert break_lines("abcdefgh", measure, 30) == [TextRange(0, 3), TextRange(3, 6), TextRange(6, 8)]


def test_an_ideograph_breaks_on_either_side() -> None:
    assert break_lines("日本語のテキスト", measure, 50) == [TextRange(0, 5), TextRange(5, 8)]
    assert break_lines("abc 日本語", measure, 50) == [TextRange(0, 5), TextRange(5, 7)]


def test_a_width_narrower_than_a_character_still_keeps_one_per_line() -> None:
    assert break_lines("abc", measure, 5) == [TextRange(0, 1), TextRange(1, 2), TextRange(2, 3)]


# --- the caret in the lines -------------------------------------------------------


def test_a_caret_at_a_soft_break_sits_on_the_next_line_and_at_a_hard_break_on_its_own() -> None:
    soft = break_lines("hello world", measure, 50)
    assert line_of(soft, 6) == 1
    assert line_of(soft, 11) == 1

    hard = break_lines("ab\ncd", measure)
    assert line_of(hard, 2) == 0
    assert line_of(hard, 3) == 1


def test_caret_x_measures_from_the_line_start() -> None:
    lines = break_lines("ab\ncd", measure)
    assert caret_x("ab\ncd", lines[1], 4, measure) == 10.0


def test_index_at_picks_the_nearer_boundary_and_clamps_to_the_line() -> None:
    lines = break_lines("ab\ncd", measure)
    assert index_at("ab\ncd", lines[1], -3.0, measure) == 3
    assert index_at("ab\ncd", lines[1], 4.0, measure) == 3
    assert index_at("ab\ncd", lines[1], 6.0, measure) == 4
    assert index_at("ab\ncd", lines[1], 99.0, measure) == 5


# --- vertical motion --------------------------------------------------------------


def test_down_keeps_the_x_and_up_returns() -> None:
    text = "abcd\nef\nghij"
    lines = break_lines(text, measure)

    down, goal = move_lines(_at(text, 3), lines, 1, measure)
    assert down == _at(text, 7) and goal == 30.0
    down_again, goal = move_lines(down, lines, 1, measure, goal_x=goal)
    assert down_again == _at(text, 11), "the short line in between did not pull the caret left"
    up, _ = move_lines(down_again, lines, -1, measure, goal_x=goal)
    assert up == _at(text, 7)


def test_above_the_first_line_is_the_start_and_below_the_last_the_end() -> None:
    text = "ab\ncd"
    lines = break_lines(text, measure)
    assert move_lines(_at(text, 1), lines, -1, measure)[0] == _at(text, 0)
    assert move_lines(_at(text, 4), lines, 1, measure)[0] == _at(text, 5)
    assert move_lines(_at(text, 0), lines, -1, measure)[0] is None


def test_select_extends_from_the_anchor_across_lines() -> None:
    text = "ab\ncd"
    lines = break_lines(text, measure)
    moved, _ = move_lines(_at(text, 1), lines, 1, measure, select=True)
    assert moved == TextEditingValue(text, TextRange(1, 4))


def test_line_edge_stops_at_the_wrapped_line() -> None:
    text = "hello world"
    lines = break_lines(text, measure, 50)
    assert line_edge(_at(text, 8), lines, end=False, select=False) == _at(text, 6)
    assert line_edge(_at(text, 8), lines, end=True, select=False) == _at(text, 11)
    assert line_edge(_at(text, 6), lines, end=False, select=False) is None
    assert line_edge(_at(text, 8), lines, end=True, select=True) == TextEditingValue(text, TextRange(8, 11))
