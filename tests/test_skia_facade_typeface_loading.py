import ast
import builtins
import os
import sys
from pathlib import Path

import pytest


def _reset_skia_import_state() -> None:
    import nuiitivet.rendering.skia.skia_module as skia_module

    from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests

    skia_module._reset_skia_import_state_for_tests()
    _clear_log_once_keys_for_tests()

    import nuiitivet.rendering.skia.font as skia_font

    skia_font._clear_typeface_caches_for_tests()


def _reset_fake_skia_counters() -> None:
    _FakeSkia.Data.make_from_bytes_calls = 0
    _FakeSkia.Data.make_with_copy_calls = 0
    _FakeSkia.Data.make_from_file_name_calls = 0
    _FakeSkia.Typeface.make_from_data_calls = 0
    _FakeSkia.Typeface.make_from_file_calls = 0


def test_typeface_from_bytes_raises_runtime_error_when_skia_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_skia_import_state()

    sys.modules.pop("skia", None)

    original_import = builtins.__import__

    def fake_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: list[str] | None = None,
        level: int = 0,
    ) -> object:
        if name == "skia":
            raise ImportError("skia not installed")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from nuiitivet.rendering.skia.font import typeface_from_bytes

    with pytest.raises(RuntimeError):
        typeface_from_bytes(b"abc")


class _FakeSkia:
    class Data:
        make_from_bytes_calls = 0
        make_with_copy_calls = 0
        make_from_file_name_calls = 0

        @classmethod
        def MakeFromBytes(cls, _data: bytes):
            cls.make_from_bytes_calls += 1
            raise RuntimeError("no MakeFromBytes")

        @classmethod
        def MakeWithCopy(cls, data: bytes):
            cls.make_with_copy_calls += 1
            return ("data", bytes(data))

        @classmethod
        def MakeFromFileName(cls, path: str):
            cls.make_from_file_name_calls += 1
            return ("file", os.path.abspath(path))

    class Typeface:
        make_from_data_calls = 0
        make_from_file_calls = 0

        @classmethod
        def MakeFromData(cls, data_obj: object):
            cls.make_from_data_calls += 1
            return ("typeface", data_obj)

        @classmethod
        def MakeFromFile(cls, _path: str):
            cls.make_from_file_calls += 1
            raise RuntimeError("no MakeFromFile")


def test_typeface_from_bytes_fallback_and_cache(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _reset_skia_import_state()
    _reset_fake_skia_counters()

    monkeypatch.setitem(sys.modules, "skia", _FakeSkia)

    caplog.set_level("DEBUG")

    from nuiitivet.rendering.skia.font import typeface_from_bytes

    try:
        tf1 = typeface_from_bytes(b"hello")
        tf2 = typeface_from_bytes(b"hello")
    finally:
        _reset_skia_import_state()

    assert tf1 == tf2
    assert _FakeSkia.Data.make_with_copy_calls == 1
    assert _FakeSkia.Typeface.make_from_data_calls == 1

    # The fallback log should be emitted once.
    msgs = [rec.getMessage() for rec in caplog.records]
    assert any("falling back to MakeWithCopy" in m for m in msgs)


def test_typeface_from_file_fallback_and_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset_skia_import_state()
    _reset_fake_skia_counters()

    monkeypatch.setitem(sys.modules, "skia", _FakeSkia)

    font_path = tmp_path / "fake.ttf"
    font_path.write_bytes(b"fakefont")

    from nuiitivet.rendering.skia.font import typeface_from_file

    try:
        tf1 = typeface_from_file(str(font_path))
        tf2 = typeface_from_file(str(font_path))
    finally:
        _reset_skia_import_state()

    assert tf1 == tf2
    assert _FakeSkia.Data.make_from_file_name_calls == 1
    assert _FakeSkia.Typeface.make_from_data_calls >= 1


def test_widgets_have_no_direct_skia_imports_or_symbol_usage() -> None:
    root = Path(__file__).resolve().parents[1]
    widgets_dir = root / "src" / "nuiitivet" / "widgets"

    py_files = sorted(widgets_dir.rglob("*.py"))
    assert py_files

    offenders: list[str] = []

    for path in py_files:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "skia":
                        offenders.append(str(path))
            elif isinstance(node, ast.ImportFrom):
                if node.module == "skia":
                    offenders.append(str(path))
            elif isinstance(node, ast.Name):
                if node.id == "skia":
                    offenders.append(str(path))

    assert offenders == []
