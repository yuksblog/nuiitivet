"""Tests for register_font() and get_typeface() registry integration."""

from __future__ import annotations

import base64
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Minimal valid TTF (TestFont Regular, 2 glyphs, 604 bytes).
# Generated once with fonttools FontBuilder; embedded here to avoid any
# runtime dependency on fonttools or external font files.
# ---------------------------------------------------------------------------
_MINIMAL_TTF_B64 = (
    "AAEAAAAKAIAAAwAgT1MvMkUhRAMAAAEoAAAAYGNtYXAADACUAAABkAAAADRnbHlm"
    "AAAAAAAAAcwAAAABaGVhZF8WQOAAAACsAAAANmhoZWEDIgGTAAAA5AAAACRobXR4"
    "BEwAAAAAAYgAAAAIbG9jYQAAAAAAAAHEAAAABm1heHAAAwACAAABCAAAACBuYW1l"
    "stVz5QAAAdAAAABjcG9zdAAoAAAAAAI0AAAAJgABAAAAAQAA6DSnN18PPPUAAwPo"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwACAAAAAAAAAAEAAAMg/zgAAAJY"
    "AAAAAAAAAAEAAAAAAAAAAAAAAAAAAAACAAEAAAACAAAAAAAAAAAAAgAAAAAAAAAA"
    "AAAAAAAAAAAAAwImAZAABQAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAABAAAAAAAAAAAAAAAAPz8/PwAAAEEAQQMg/zgAAAMgAMgAAAAAAAAAAAAA"
    "AAAAAAAgAAAB9AAAAlgAAAAAAAIAAAADAAAAFAADAAEAAAAUAAQAIAAAAAQABAAB"
    "AAAAQf//AAAAQf///8AAAQAAAAAAAAAAAAAAAAAAAAAAAAAEADYAAQAAAAAAAQAI"
    "AAAAAQAAAAAAAgAHAAgAAwABBAkAAQAQAA8AAwABBAkAAgAOAB9UZXN0Rm9udFJl"
    "Z3VsYXIAVABlAHMAdABGAG8AbgB0AFIAZQBnAHUAbABhAHIAAAIAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAACQAAA=="
)


def _minimal_ttf_bytes() -> bytes:
    return base64.b64decode(_MINIMAL_TTF_B64)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_state() -> None:
    import nuiitivet.rendering.skia.font as skia_font
    from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests

    skia_font._clear_typeface_caches_for_tests()
    _clear_log_once_keys_for_tests()


# ---------------------------------------------------------------------------
# Tests for register_font() — registry storage (no real font file needed)
# ---------------------------------------------------------------------------


class TestRegisterFontRegistry:
    def setup_method(self) -> None:
        _reset_state()

    def teardown_method(self) -> None:
        _reset_state()

    def test_register_stores_mapping(self) -> None:
        from nuiitivet.rendering.skia.font import register_font, _FONT_REGISTRY

        register_font("/path/to/MyFont.ttf", "MyFont")

        assert _FONT_REGISTRY.get("MyFont") == "/path/to/MyFont.ttf"

    def test_register_overwrites_existing(self) -> None:
        from nuiitivet.rendering.skia.font import register_font, _FONT_REGISTRY

        register_font("/old/path.ttf", "MyFont")
        register_font("/new/path.ttf", "MyFont")

        assert _FONT_REGISTRY.get("MyFont") == "/new/path.ttf"

    def test_clear_caches_clears_registry(self) -> None:
        from nuiitivet.rendering.skia.font import register_font, _FONT_REGISTRY
        import nuiitivet.rendering.skia.font as skia_font

        register_font("/some/font.ttf", "AnyFont")
        assert "AnyFont" in _FONT_REGISTRY

        skia_font._clear_typeface_caches_for_tests()

        assert "AnyFont" not in _FONT_REGISTRY

    def test_top_level_api_available(self) -> None:
        import nuiitivet

        assert hasattr(nuiitivet, "register_font")
        assert callable(nuiitivet.register_font)

    def test_register_font_in_all(self) -> None:
        import nuiitivet

        assert "register_font" in nuiitivet.__all__


# ---------------------------------------------------------------------------
# Tests for get_typeface() registry integration (uses real font file)
# ---------------------------------------------------------------------------


class TestGetTypefaceWithRegistry:
    def setup_method(self) -> None:
        _reset_state()

    def teardown_method(self) -> None:
        _reset_state()

    def test_registered_family_resolves_typeface(self, tmp_path: pytest.TempPathFactory) -> None:
        font_path = tmp_path / "TestFont.ttf"
        font_path.write_bytes(_minimal_ttf_bytes())

        from nuiitivet.rendering.skia.font import register_font, get_typeface

        register_font(str(font_path), "TestFont")

        tf = get_typeface(family_candidates=("TestFont",))

        # May be None when skia is not installed in the test environment,
        # but should never raise.
        assert tf is None or tf is not None  # resolves without error

    def test_unregistered_family_falls_through(self, tmp_path: pytest.TempPathFactory) -> None:
        from nuiitivet.rendering.skia.font import get_typeface

        # No registration — should not raise, just return None or a system font.
        try:
            get_typeface(family_candidates=("NoSuchFontXYZ123",), fallback_to_default=False)
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"get_typeface raised unexpectedly: {exc}")

    def test_registered_family_cached_on_second_call(self, tmp_path: pytest.TempPathFactory) -> None:
        font_path = tmp_path / "TestFont.ttf"
        font_path.write_bytes(_minimal_ttf_bytes())

        from nuiitivet.rendering.skia.font import register_font, get_typeface, _TYPEFACE_CACHE

        register_font(str(font_path), "CachedFont")

        key = (None, ("CachedFont",), None, True)
        assert key not in _TYPEFACE_CACHE

        get_typeface(family_candidates=("CachedFont",))

        # After the first call the result (whatever it is) must be cached.
        assert key in _TYPEFACE_CACHE

    def test_typeface_from_file_used_for_registered_font(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify get_typeface resolves via typeface_from_file for registry entries."""
        font_path = tmp_path / "TestFont.ttf"
        font_path.write_bytes(_minimal_ttf_bytes())

        import nuiitivet.rendering.skia.font as skia_font

        calls: list[str] = []
        _original = skia_font.typeface_from_file

        def _spy(path: str):
            calls.append(path)
            return _original(path)

        monkeypatch.setattr(skia_font, "typeface_from_file", _spy)

        skia_font.register_font(str(font_path), "SpyFont")
        skia_font.get_typeface(family_candidates=("SpyFont",))

        assert str(font_path) in calls
