"""Tests for get_default_font_fallbacks() — platform lists, locale, caching."""

from __future__ import annotations

import sys

import pytest

import nuiitivet.rendering.skia.font as skia_font


@pytest.fixture(autouse=True)
def _reset_fallback_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(skia_font, "_USER_DEFAULT_FONT_FAMILY", None)
    monkeypatch.setattr(skia_font, "_DEFAULT_FALLBACKS_CACHE", None)
    yield
    skia_font._DEFAULT_FALLBACKS_CACHE = None


def _force_language(monkeypatch: pytest.MonkeyPatch, lang: str | None) -> None:
    monkeypatch.setattr(skia_font, "_detect_ui_language", lambda: lang)


class TestPlatformLists:
    def test_darwin_head_is_weight_complete_system_font(self, monkeypatch) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        fallbacks = skia_font._platform_font_fallbacks(prefer_cjk=False)
        assert fallbacks[0] == ".AppleSystemUIFont"
        # 400/700-only families must never outrank a true-Medium family.
        assert fallbacks.index("Arial") > fallbacks.index("Helvetica Neue")
        assert fallbacks.index("Hiragino Kaku Gothic ProN") > fallbacks.index("Hiragino Sans")

    def test_win32_head_is_weight_complete_system_font(self, monkeypatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        fallbacks = skia_font._platform_font_fallbacks(prefer_cjk=False)
        assert fallbacks[0] == "Segoe UI Variable"
        assert fallbacks.index("Yu Gothic") < fallbacks.index("Yu Gothic UI")
        assert fallbacks.index("Meiryo") > fallbacks.index("Yu Gothic UI")

    def test_linux_head_is_noto(self, monkeypatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        fallbacks = skia_font._platform_font_fallbacks(prefer_cjk=False)
        assert fallbacks[0] == "Noto Sans"
        assert fallbacks[-1].startswith("Noto Sans")  # CJK tail present

    def test_cjk_tail_present_for_non_cjk_locale(self, monkeypatch) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        fallbacks = skia_font._platform_font_fallbacks(prefer_cjk=False)
        assert "Hiragino Sans" in fallbacks
        assert fallbacks.index("Hiragino Sans") > fallbacks.index(".AppleSystemUIFont")

    def test_cjk_first_for_ja(self, monkeypatch) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        fallbacks = skia_font._platform_font_fallbacks(prefer_cjk=True)
        assert fallbacks[0] == "Hiragino Sans"
        assert ".AppleSystemUIFont" in fallbacks


class TestLanguageDetection:
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX env-var path")
    def test_reads_lang_family_env_vars(self, monkeypatch) -> None:
        for var in ("LC_ALL", "LC_CTYPE", "LANG"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("LANG", "ja_JP.UTF-8")
        assert skia_font._detect_ui_language() == "ja"

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX env-var path")
    def test_lc_all_wins_over_lang(self, monkeypatch) -> None:
        monkeypatch.setenv("LC_ALL", "de_DE.UTF-8")
        monkeypatch.setenv("LANG", "ja_JP.UTF-8")
        assert skia_font._detect_ui_language() == "de"

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX env-var path")
    def test_c_locale_is_skipped(self, monkeypatch) -> None:
        for var in ("LC_ALL", "LC_CTYPE", "LANG"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("LANG", "C.UTF-8")
        assert skia_font._detect_ui_language() is None

    def test_ja_prefers_cjk_in_public_list(self, monkeypatch) -> None:
        _force_language(monkeypatch, "ja")
        fallbacks = skia_font.get_default_font_fallbacks()
        assert fallbacks[0] == skia_font._platform_font_fallbacks(prefer_cjk=True)[0]

    def test_non_ja_prefers_western_in_public_list(self, monkeypatch) -> None:
        _force_language(monkeypatch, "en")
        fallbacks = skia_font.get_default_font_fallbacks()
        assert fallbacks[0] == skia_font._platform_font_fallbacks(prefer_cjk=False)[0]


class TestCaching:
    def test_list_is_computed_once(self, monkeypatch) -> None:
        calls = []
        _force_language(monkeypatch, "en")
        original = skia_font._platform_font_fallbacks

        def counting(prefer_cjk: bool):
            calls.append(prefer_cjk)
            return original(prefer_cjk)

        monkeypatch.setattr(skia_font, "_platform_font_fallbacks", counting)
        first = skia_font.get_default_font_fallbacks()
        second = skia_font.get_default_font_fallbacks()
        assert first is second
        assert len(calls) == 1

    def test_set_default_font_family_prepends_and_invalidates(self, monkeypatch) -> None:
        _force_language(monkeypatch, "en")
        base = skia_font.get_default_font_fallbacks()
        skia_font.set_default_font_family("MyFont")
        assert skia_font.get_default_font_fallbacks() == ("MyFont",) + base
        skia_font.set_default_font_family(None)
        assert skia_font.get_default_font_fallbacks() == base

    def test_test_clearer_resets_cache(self, monkeypatch) -> None:
        _force_language(monkeypatch, "en")
        skia_font.get_default_font_fallbacks()
        skia_font._clear_typeface_caches_for_tests()
        assert skia_font._DEFAULT_FALLBACKS_CACHE is None
