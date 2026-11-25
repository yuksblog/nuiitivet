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


def test_mixed_cjk_and_ascii_fills_each_line():
    text = "露光 1000 [us] のため、実際には約 1000 [lines/s] しか出ません。"
    _t, lines, _ = _lines(text, width=20)
    assert lines == ["露光 1000 [us] のため、実際に", "は約 1000 [lines/s] しか", "出ません。"]


def test_line_breaks_between_cjk_and_a_word():
    _t, lines, _ = _lines("abcd世efgh", width=6)
    assert lines == ["abcd世", "efgh"]


def test_word_beside_cjk_breaks_at_its_space_only():
    _t, lines, _ = _lines("hello 世界 world", width=7)
    assert lines == ["hello 世", "界 world"]


def test_no_line_starts_with_closing_punctuation():
    _t, lines, _ = _lines("あいう。えお", width=3)
    assert lines == ["あい", "う。え", "お"]


def test_no_line_ends_with_an_opening_bracket():
    _t, lines, _ = _lines("あい「うえ」お", width=3)
    assert lines == ["あい", "「う", "え」お"]


def test_no_line_starts_with_small_kana_or_the_long_vowel_mark():
    _t, lines, _ = _lines("クロップデータ", width=2)
    assert lines == ["ク", "ロッ", "プ", "デー", "タ"]


def test_ascii_punctuation_stays_with_the_cjk_beside_it():
    _t, lines, _ = _lines("あい(うえ)お", width=3)
    assert lines == ["あい", "(う", "え)お"]


def test_run_that_may_not_break_is_char_broken_when_too_long():
    _t, lines, _ = _lines("あ。。。。", width=2)
    assert lines == ["あ。", "。。", "。"]


def test_combining_mark_stays_with_its_base():
    voiced_ka = "か\N{COMBINING KATAKANA-HIRAGANA VOICED SOUND MARK}"
    _t, lines, _ = _lines("あ" + voiced_ka, width=2)
    assert lines == ["あ", voiced_ka]


def test_emoji_sequence_stays_whole():
    thumbs_up_with_skin_tone = "\U0001f44d\U0001f3fd"
    family = "\U0001f468\N{ZERO WIDTH JOINER}\U0001f469"
    _t, lines, _ = _lines("あい" + thumbs_up_with_skin_tone + family, width=3)
    assert lines == ["あい", thumbs_up_with_skin_tone, family]

    flag_of_england = "\U0001f3f4\U000e0067\U000e0062\U000e007f"
    _t, lines, _ = _lines("ああ" + flag_of_england, width=4)
    assert lines == ["ああ", flag_of_england]


def test_no_break_space_holds_the_cjk_on_both_sides():
    held = "い\N{NO-BREAK SPACE}う"
    _t, lines, _ = _lines("あ" + held + "え", width=3)
    assert lines == ["あ", held, "え"]


def test_decomposed_hangul_syllable_stays_whole():
    ga = "\N{HANGUL CHOSEONG KIYEOK}\N{HANGUL JUNGSEONG A}"
    _t, lines, _ = _lines(ga + ga, width=3)
    assert lines == [ga, ga]


def test_halfwidth_katakana_breaks_like_fullwidth():
    _t, lines, _ = _lines("あいｱｲｳｴｵ", width=4)
    assert lines == ["あいｱｲ", "ｳｴｵ"]

    _t, lines, _ = _lines("ｱｲｶﾞ", width=3)
    assert lines == ["ｱｲ", "ｶﾞ"]


def test_no_line_starts_with_a_fullwidth_tilde():
    _t, lines, _ = _lines("あい～う", width=2)
    assert lines == ["あ", "い～", "う"]


def test_no_line_starts_with_a_slash_or_a_hyphen():
    _t, lines, _ = _lines("東京/大阪", width=2)
    assert lines == ["東", "京/", "大阪"]

    _t, lines, _ = _lines("あい-う", width=2)
    assert lines == ["あ", "い-", "う"]


def test_no_line_starts_with_a_unit_sign():
    _t, lines, _ = _lines("気温℃です", width=2)
    assert lines == ["気", "温℃", "です"]


def test_no_line_ends_with_a_currency_sign():
    _t, lines, _ = _lines("約€百", width=2)
    assert lines == ["約", "€百"]


def test_quotation_mark_holds_the_side_it_encloses():
    _t, lines, _ = _lines("あ«い»う", width=3)
    assert lines == ["あ", "«い»", "う"]


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
