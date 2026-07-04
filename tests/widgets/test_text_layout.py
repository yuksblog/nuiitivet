"""Backend-independent tests for Text line layout, wrapping and truncation.

These exercise the pure line-resolution helpers on ``TextBase`` using a
deterministic ``measure`` callable (1 unit per character), so they run without
a skia backend.
"""

from nuiitivet.widgets.text import TextBase


def measure(s: str) -> float:
    """Deterministic width: one unit per character."""
    return float(len(s))


def _lines(text, width, **kwargs):
    t = TextBase(text, **kwargs)
    laid, overflowed = t._layout_lines(text, float(width), measure)
    return t, laid, overflowed


def test_hard_newlines_are_honored():
    _t, lines, overflowed = _lines("a\nb\nc", width=0)  # unbounded width
    assert lines == ["a", "b", "c"]
    assert overflowed is False


def test_newline_variants_normalized():
    _t, lines, _ = _lines("a\r\nb\rc", width=0)
    assert lines == ["a", "b", "c"]


def test_soft_wrap_by_words():
    _t, lines, _ = _lines("aaa bbb ccc", width=7, soft_wrap=True)
    assert lines == ["aaa bbb", "ccc"]


def test_soft_wrap_disabled_keeps_single_line():
    _t, lines, _ = _lines("aaa bbb ccc", width=7, soft_wrap=False)
    assert lines == ["aaa bbb ccc"]


def test_long_word_is_char_broken():
    _t, lines, _ = _lines("aaaaaaaa", width=3, soft_wrap=True)
    assert lines == ["aaa", "aaa", "aa"]


def test_max_lines_caps_and_flags_overflow():
    _t, lines, overflowed = _lines("a\nb\nc\nd", width=0, max_lines=2)
    assert lines == ["a", "b"]
    assert overflowed is True


def test_max_lines_below_one_clamps():
    t = TextBase("x", max_lines=0)
    assert t._max_lines == 1


def test_ellipsis_tail():
    t = TextBase("x", overflow="ellipsis", truncation="tail")
    out = t._truncate_line("abcdefgh", 4.0, measure)
    assert out == "abc…"


def test_ellipsis_head():
    t = TextBase("x", overflow="ellipsis", truncation="head")
    out = t._truncate_line("abcdefgh", 4.0, measure)
    assert out == "…fgh"


def test_ellipsis_middle():
    t = TextBase("x", overflow="ellipsis", truncation="middle")
    out = t._truncate_line("abcdefgh", 5.0, measure)
    # 5 units: ellipsis (1) + 4 chars, split 2 prefix / 2 suffix.
    assert out == "ab…gh"


def test_apply_ellipsis_marks_last_line_when_line_limited():
    t = TextBase("x", overflow="ellipsis", truncation="tail", max_lines=1)
    laid, overflowed = t._layout_lines("aaaa\nbbbb", 0.0, measure)
    assert overflowed is True
    # avail_w=0 disables ellipsis; provide a bounded width instead.
    out = t._apply_ellipsis(laid, overflowed, 3.0, measure)
    assert out[-1].endswith("…")


def test_apply_ellipsis_noop_when_visible():
    t = TextBase("x", overflow="visible")
    laid, overflowed = t._layout_lines("abcdefgh", 3.0, measure)
    assert t._apply_ellipsis(laid, overflowed, 3.0, measure) == laid
