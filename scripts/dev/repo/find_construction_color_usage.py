"""Scan src/nuiitivet for assignments to color-like attributes inside __init__.

This script performs a conservative AST-based scan and prints locations where
an __init__ method assigns to common color attributes (bgcolor, border_color,
shadow_color, color, fill_color, stroke_color). It classifies the RHS as:
 - literal_hex: string literal like "#RRGGBB"
 - material_token: attribute access like material.PRIMARY
 - theme_get: call to theme_manager.current.get(...) or ThemeManager.get
 - colorrole: Name or attribute referring to ColorRole
 - other: anything else

Run from the repository root; it prints a human-readable report.
"""

from __future__ import annotations

import ast
import os
from typing import List, Tuple

ROOT = os.path.join(os.path.dirname(__file__), "..")
PKG = os.path.abspath(os.path.join(ROOT, "nuiitivet"))
TARGET_DIR = PKG

COLOR_ATTRS = {
    "bgcolor",
    "border_color",
    "shadow_color",
    "color",
    "fill_color",
    "stroke_color",
    "mark_p",
    "mark_color",
}


class AssignVisitor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.reports: List[Tuple[int, str, str]] = []  # lineno, attr, kind
        self.in_init = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev = self.in_init
        if node.name == "__init__":
            self.in_init = True
            # scan body for assigns
            for n in node.body:
                self.visit(n)
        else:
            # don't traverse into other functions
            pass
        self.in_init = prev

    def visit_Assign(self, node: ast.Assign):
        if not self.in_init:
            return
        # only handle simple targets like self.xxx
        for t in node.targets:
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                attr = t.attr
                if attr in COLOR_ATTRS:
                    kind = classify_rhs(node.value)
                    self.reports.append((getattr(node, "lineno", 0), attr, kind))

    def visit_AnnAssign(self, node: ast.AnnAssign):
        # handle annotated assigns too
        if not self.in_init:
            return
        t = node.target
        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
            attr = t.attr
            if attr in COLOR_ATTRS and node.value is not None:
                kind = classify_rhs(node.value)
                self.reports.append((getattr(node, "lineno", 0), attr, kind))


def classify_rhs(node: ast.AST) -> str:
    # string literal hex
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        v = node.value
        if v.startswith("#"):
            return "literal_hex"
        return "literal_str"

    # tuple like (ColorRole.X, 0.24)
    if isinstance(node, ast.Tuple) and len(node.elts) == 2:
        first = node.elts[0]
        if (
            isinstance(first, ast.Attribute)
            and isinstance(first.value, ast.Name)
            and first.value.id in {"ColorRole", "theme"}
        ):
            return "colorrole_tuple"
        if isinstance(first, ast.Name) and first.id == "ColorRole":
            return "colorrole_tuple"

    # Name or Attribute referring to ColorRole or material
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "material":
            return "material_token"
        if isinstance(node.value, ast.Name) and node.value.id == "ColorRole":
            return "colorrole"
        # theme_manager.current.get(...)
        if (
            isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "theme_manager"
        ):
            return "theme_get_like"

    if isinstance(node, ast.Call):
        # look for theme_manager.current.get(...) or ThemeManager.get
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr == "get":
                # could be theme_manager.current.get or theme.manager.get
                if (
                    isinstance(func.value, ast.Attribute)
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id in {"theme_manager", "theme"}
                ):
                    return "theme_get"
                if isinstance(func.value, ast.Name) and func.value.id in {"theme_manager", "manager", "theme"}:
                    return "theme_get"
        return "call"

    if isinstance(node, ast.Name):
        if node.id == "ColorRole":
            return "colorrole"
        return "name"

    return "other"


def scan_file(path: str) -> List[Tuple[int, str, str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception:
        return []
    try:
        tree = ast.parse(src, filename=path)
    except Exception:
        return []
    v = AssignVisitor(path)
    v.visit(tree)
    return v.reports


def main():
    findings = {}
    for root, dirs, files in os.walk(TARGET_DIR):
        for fn in files:
            if fn.endswith(".py"):
                p = os.path.join(root, fn)
                reps = scan_file(p)
                if reps:
                    findings[p] = reps

    if not findings:
        print("No construction-time color assignments found.")
        return

    print("Construction-time color assignments (file: lineno, attr, kind):\n")
    for f, reps in sorted(findings.items()):
        print(f"{f}:")
        for lineno, attr, kind in reps:
            print(f"  {lineno}: self.{attr} -> {kind}")
        print()


if __name__ == "__main__":
    main()
