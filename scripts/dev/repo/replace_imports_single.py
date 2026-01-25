"""Apply a single AST-based import replacement from the project's mapping.

Usage:
    python scripts/dev/repo/replace_imports_single.py --key nuiitivet.ui.widgets [--apply]

This script lets us apply one mapping at a time so we can validate tests
between batches during the migration.
"""

from __future__ import annotations

import ast
import argparse
import pathlib
from typing import Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]

# canonical mapping from replace_imports.py. We will select one key to apply.
CANONICAL: Dict[str, str] = {
    "nuiitivet.ui.widgets": "nuiitivet.widgets",
    "nuiitivet.ui.layouts": "nuiitivet.layout",
    "nuiitivet.ui.styles": "nuiitivet.theme.styles",
    "nuiitivet.ui.material_symbols": "nuiitivet.symbols.material_symbols",
    "nuiitivet.ui": "nuiitivet",
}


def replace_module_name(name: str, mapping: Dict[str, str]) -> str:
    for old, new in mapping.items():
        if name == old or name.startswith(old + "."):
            return name.replace(old, new, 1)
    return name


class ImportRewriter(ast.NodeTransformer):
    def __init__(self, mapping: Dict[str, str]) -> None:
        super().__init__()
        self.mapping = mapping
        self.changes: List[Tuple[int, str, str]] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST:  # type: ignore[override]
        if node.module:
            new_module = replace_module_name(node.module, self.mapping)
            if new_module != node.module:
                self.changes.append((node.lineno, node.module, new_module))
                node.module = new_module
        return node

    def visit_Import(self, node: ast.Import) -> ast.AST:  # type: ignore[override]
        for alias in node.names:
            new_name = replace_module_name(alias.name, self.mapping)
            if new_name != alias.name:
                self.changes.append((node.lineno, alias.name, new_name))
                alias.name = new_name
        return node


def process_file(path: pathlib.Path, mapping: Dict[str, str], apply: bool = False) -> List[Tuple[int, str, str]]:
    src = path.read_text(encoding="utf8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    rewriter = ImportRewriter(mapping)
    new_tree = rewriter.visit(tree)
    if rewriter.changes and apply:
        new_src = ast.unparse(new_tree)
        path.write_text(new_src, encoding="utf8")
    return rewriter.changes


def find_py_files(root: pathlib.Path) -> List[pathlib.Path]:
    return [p for p in root.rglob("*.py") if ".venv" not in p.parts]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, help="The mapping key to apply")
    parser.add_argument("--apply", action="store_true", help="Write changes to files")
    parser.add_argument("--root", default=str(ROOT / "src"), help="Root path to search")
    args = parser.parse_args()

    if args.key not in CANONICAL:
        print(f"Unknown mapping key: {args.key}")
        print("Known keys:")
        for k in CANONICAL:
            print(f"  {k} -> {CANONICAL[k]}")
        return 2

    mapping = {args.key: CANONICAL[args.key]}

    root = pathlib.Path(args.root)
    files = find_py_files(root) + find_py_files(pathlib.Path("tests")) + find_py_files(pathlib.Path("scripts"))
    files = sorted(set(files))

    total_changes = 0
    for f in files:
        changes = process_file(f, mapping, apply=args.apply)
        if changes:
            print(f"{f}:")
            for lineno, old, new in changes:
                total_changes += 1
                print(f"  {lineno}: {old} -> {new}")

    print(f"\nProcessed {len(files)} files; planned changes: {total_changes}")
    if args.apply:
        print("Changes applied. Run tests and mypy.")
    else:
        print("Dry-run complete. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
