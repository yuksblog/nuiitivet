"""The PyInstaller hook lists every module that a lazy export imports.

The hook file imports ``PyInstaller.utils.hooks``. The tests replace that module
with a stub, so they run without PyInstaller installed.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import pathlib
import sys
import types
from typing import Any

import pytest

import nuiitivet
import nuiitivet._pyinstaller
import nuiitivet.material as material
import nuiitivet.matplotlib as nv_matplotlib
from nuiitivet._pyinstaller import EXCLUDED_PACKAGES, MATPLOTLIB_WIDGET_MODULES

_PACKAGE_DIR = pathlib.Path(nuiitivet.__file__).parent
_HOOK = _PACKAGE_DIR / "_pyinstaller" / "hook-nuiitivet.py"


def _load_hook(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    stub = types.ModuleType("PyInstaller.utils.hooks")
    stub.collect_data_files = lambda package: []  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "PyInstaller", types.ModuleType("PyInstaller"))
    monkeypatch.setitem(sys.modules, "PyInstaller.utils", types.ModuleType("PyInstaller.utils"))
    monkeypatch.setitem(sys.modules, "PyInstaller.utils.hooks", stub)
    spec = importlib.util.spec_from_file_location("hook_nuiitivet", _HOOK)
    assert spec is not None and spec.loader is not None
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    return hook


def _imported_by_lazy_exports(
    monkeypatch: pytest.MonkeyPatch, module: types.ModuleType, names: list[str], target: Any, attr: str
) -> set[str]:
    """Call ``module.__getattr__`` for each name and record the modules it imports."""
    imported: set[str] = set()
    real = importlib.import_module

    def spy(name: str, package: str | None = None) -> types.ModuleType:
        imported.add(importlib.util.resolve_name(name, package) if name.startswith(".") else name)
        return real(name, package)

    monkeypatch.setattr(target, attr, spy)
    for name in names:
        module.__getattr__(name)
    return imported


def test_hook_lists_every_module_the_material_exports_import(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("matplotlib")
    imported = _imported_by_lazy_exports(monkeypatch, material, list(material._EXPORTS), importlib, "import_module")
    missing = imported - set(_load_hook(monkeypatch).hiddenimports)
    assert missing == set(), f"lazy exports import modules the PyInstaller hook misses: {sorted(missing)}"


def test_hook_lists_every_module_the_matplotlib_exports_import(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("matplotlib")
    imported = _imported_by_lazy_exports(
        monkeypatch, nv_matplotlib, list(nv_matplotlib.__all__), nv_matplotlib, "import_module"
    )
    missing = imported - set(_load_hook(monkeypatch).hiddenimports)
    assert missing == set(), f"lazy exports import modules the PyInstaller hook misses: {sorted(missing)}"


def test_hook_excludes_the_dev_testing_and_skills_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nuiitivet._pyinstaller, "matplotlib_installed", lambda: True)
    hook = _load_hook(monkeypatch)
    assert set(hook.excludedimports) == {"nuiitivet.dev", "nuiitivet.testing", "nuiitivet.skills"}
    assert [name for name in hook.hiddenimports if name.startswith(EXCLUDED_PACKAGES)] == []
    assert set(MATPLOTLIB_WIDGET_MODULES) <= set(hook.hiddenimports)


def test_hook_leaves_out_the_matplotlib_widgets_without_matplotlib(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nuiitivet._pyinstaller, "matplotlib_installed", lambda: False)
    hook = _load_hook(monkeypatch)
    assert set(MATPLOTLIB_WIDGET_MODULES) <= set(hook.excludedimports)
    assert set(MATPLOTLIB_WIDGET_MODULES).isdisjoint(hook.hiddenimports)
    assert "nuiitivet.material.window" in hook.hiddenimports


def test_only_material_and_matplotlib_import_exports_lazily() -> None:
    """A new module ``__getattr__`` needs its modules in ``hidden_imports``."""
    lazy: set[str] = set()
    for path in _PACKAGE_DIR.rglob("*.py"):
        module = ".".join(("nuiitivet", *path.relative_to(_PACKAGE_DIR).with_suffix("").parts))
        module = module.removesuffix(".__init__")
        if module.startswith(EXCLUDED_PACKAGES):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(isinstance(node, ast.FunctionDef) and node.name == "__getattr__" for node in tree.body):
            lazy.add(module)
    assert lazy == {"nuiitivet.material", "nuiitivet.matplotlib"}
