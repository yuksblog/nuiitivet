"""List all files referencing `nuiitivet.ui` in the repository.

Usage: python3 scripts/dev/repo/list_ui_references.py [--root src]
"""

from __future__ import annotations

import argparse
import pathlib
import re


def find_files(root: pathlib.Path):
    return [p for p in root.rglob("*.py") if ".venv" not in p.parts]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="src", help="Root folder to scan")
    args = parser.parse_args()

    root = pathlib.Path(args.root)
    files = find_files(root)
    pattern = re.compile(r"\bnuiitivet\.ui(?:\b|\.)")

    for f in sorted(files):
        try:
            txt = f.read_text(encoding="utf8")
        except Exception:
            continue
        if pattern.search(txt):
            print(f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
