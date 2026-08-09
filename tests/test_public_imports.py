"""Enforce the public import policy (issue #283).

Invariants:
1. Every symbol in ``nuiitivet.material.__all__`` is actually reachable.
2. Every core symbol (``nuiitivet.__all__``) is re-exported from the design
   system root ``nuiitivet.material``.
3. ``__all__`` lists contain no duplicates.
4. Samples import *only* ``import nuiitivet.material as nv`` — no deep imports.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

import nuiitivet as core
import nuiitivet.material as md

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SAMPLES = _ROOT / "samples"


def test_material_all_symbols_resolve() -> None:
    unresolved = [name for name in md.__all__ if not hasattr(md, name)]
    assert unresolved == [], f"material.__all__ names that do not resolve: {unresolved}"


def test_core_all_symbols_resolve() -> None:
    unresolved = [name for name in core.__all__ if not hasattr(core, name)]
    assert unresolved == [], f"nuiitivet.__all__ names that do not resolve: {unresolved}"


def test_material_reexports_every_core_symbol() -> None:
    missing = [name for name in core.__all__ if not hasattr(md, name)]
    assert missing == [], (
        "Material root must re-export every core symbol; missing: " + ", ".join(missing)
    )


@pytest.mark.parametrize("module", [core, md], ids=["nuiitivet", "nuiitivet.material"])
@pytest.mark.parametrize("name", ["Sizing", "SizingKind", "SizingLike"])
def test_sizing_vocabulary_is_public(module: object, name: str) -> None:
    """`width=` / `height=` accept a `SizingLike`, so users must be able to name it."""

    assert hasattr(module, name), f"{module.__name__}.{name} is not exported"  # type: ignore[attr-defined]


@pytest.mark.parametrize("module", [core, md], ids=["nuiitivet", "nuiitivet.material"])
def test_all_has_no_duplicates(module: object) -> None:
    names = list(module.__all__)  # type: ignore[attr-defined]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert dupes == [], f"{module.__name__} has duplicate __all__ entries: {dupes}"  # type: ignore[attr-defined]


def _sample_files() -> list[pathlib.Path]:
    return [
        f
        for f in sorted(_SAMPLES.rglob("*.py"))
        if "__pycache__" not in f.parts and f.name != "__init__.py"
    ]


def test_samples_use_only_the_single_root() -> None:
    """No sample may import from a nuiitivet submodule; only the material root."""
    offenders: list[str] = []
    for f in _sample_files():
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] == "nuiitivet":
                    offenders.append(f"{f.relative_to(_ROOT)}:{node.lineno} from {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] != "nuiitivet":
                        continue
                    if alias.name != "nuiitivet.material":
                        offenders.append(
                            f"{f.relative_to(_ROOT)}:{node.lineno} import {alias.name}"
                        )
    assert offenders == [], "Samples must use only `import nuiitivet.material as nv`:\n" + "\n".join(
        offenders
    )


def test_samples_import_cleanly() -> None:
    """Every sample module imports (module-level symbols resolve against the root)."""
    import importlib.util

    failures: list[str] = []
    for i, f in enumerate(_sample_files()):
        name = f"_sample_import_check_{i}"
        spec = importlib.util.spec_from_file_location(name, f)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        import sys

        sys.modules[name] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:  # noqa: BLE001 — report all, fail once
            failures.append(f"{f.relative_to(_ROOT)}: {type(exc).__name__}: {exc}")
        finally:
            sys.modules.pop(name, None)
    assert failures == [], "Samples failed to import:\n" + "\n".join(failures)
