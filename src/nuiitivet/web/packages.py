"""The Pyodide packages an app imports, found in its sources and resolved through Pyodide's lock file.

Pyodide ships numpy, matplotlib and the rest as wheels of its own build; a
page loads the ones it needs by name. The names come from the app's own
``import`` statements, so an app declares nothing: importing matplotlib is the
declaration.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, Iterator

from nuiitivet.web.stubs import SKIPPED_DIRS, ServerOnly

#: Imports no Pyodide package provides: the framework and what the page bundles with it, and the page's own runtime.
_BUNDLED = {"nuiitivet", "materialyoucolor", "js", "pyodide"}


def _app_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if not any(part.startswith(".") or part in SKIPPED_DIRS for part in path.relative_to(root).parts):
            yield path


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def imported_names(root: Path) -> set[str]:
    """The top-level modules the app's page imports that are neither the standard library nor the app's own.

    The server-only files are left out: what they import runs on the server,
    and a page that loaded it would load a database client it never uses.

    Args:
        root: The app's directory.
    """
    own = {path.stem for path in root.iterdir() if path.suffix == ".py"}
    own |= {path.name for path in root.iterdir() if path.is_dir()}
    server_only = ServerOnly(root)
    names: set[str] = set()
    for path in _app_files(root):
        if not server_only.covers(path):
            names |= _top_level_imports(path)
    return names - set(sys.stdlib_module_names) - own - _BUNDLED


def resolve(lock: dict[str, Any], names: set[str]) -> list[dict[str, Any]]:
    """The lock entries of the packages providing *names*, and of everything they depend on.

    A name no package provides is left out: the page then fails on that
    import as it does today, naming the module.

    Args:
        lock: Pyodide's ``pyodide-lock.json``, parsed.
        names: Top-level import names.

    Returns:
        The entries, sorted by package name.
    """
    packages: dict[str, dict[str, Any]] = lock["packages"]
    by_import: dict[str, str] = {}
    for name, entry in packages.items():
        by_import[name] = name
        for imported in entry.get("imports", ()):
            by_import.setdefault(imported, name)
    wanted = [by_import[name] for name in sorted(names) if name in by_import]
    resolved: dict[str, dict[str, Any]] = {}
    while wanted:
        name = wanted.pop()
        if name in resolved or name not in packages:
            continue
        resolved[name] = packages[name]
        wanted.extend(packages[name].get("depends", ()))
    return [resolved[name] for name in sorted(resolved)]


__all__ = ["imported_names", "resolve"]
