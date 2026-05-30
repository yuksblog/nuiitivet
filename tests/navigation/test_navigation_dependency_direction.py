"""Guardrail tests for navigation dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path


def test_navigation_does_not_import_material_layer() -> None:
    """`nuiitivet.navigation` must not depend on `nuiitivet.material`."""

    repo_root = Path(__file__).resolve().parents[1]
    navigation_root = repo_root / "src" / "nuiitivet" / "navigation"

    violations: list[str] = []
    for py_file in navigation_root.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == "nuiitivet.material" or name.startswith("nuiitivet.material."):
                        rel = py_file.relative_to(repo_root)
                        violations.append(f"{rel}:{node.lineno} imports {name}")

            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "nuiitivet.material" or module.startswith("nuiitivet.material."):
                    rel = py_file.relative_to(repo_root)
                    violations.append(f"{rel}:{node.lineno} imports from {module}")

    assert violations == []
