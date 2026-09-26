"""Packages that must not import each other, at module top level or lazily.

Navigator and Overlay are siblings over the transition kernel. An import from
one into the other would make one depend on the other again, and an import from
the kernel into either would put the kernel on top of what it serves.

Modifiers sit above the overlay: popup, tooltip and context_menu are its
clients, so an overlay import of a modifier closes a cycle.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "src" / "nuiitivet"

# (importing package, imported package)
FORBIDDEN: list[tuple[str, str]] = [
    ("overlay", "navigation"),
    ("navigation", "overlay"),
    ("transition", "navigation"),
    ("transition", "overlay"),
    ("overlay", "modifiers"),
]


def _imported_modules(path: Path) -> list[tuple[int, str]]:
    package = ".".join(("nuiitivet", *path.relative_to(SRC).parent.parts))
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                module = ".".join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ""
            found.append((node.lineno, module))
    return found


@pytest.mark.parametrize(("importer", "imported"), FORBIDDEN, ids=lambda v: v)
def test_package_does_not_import(importer: str, imported: str) -> None:
    target = f"nuiitivet.{imported}"
    violations = [
        f"{path.relative_to(SRC)}:{lineno}: {module}"
        for path in sorted((SRC / importer).rglob("*.py"))
        for lineno, module in _imported_modules(path)
        if module == target or module.startswith(target + ".")
    ]
    assert not violations, f"nuiitivet.{importer} must not import {target}:\n" + "\n".join(violations)
