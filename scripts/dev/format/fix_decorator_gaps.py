#!/usr/bin/env python3
"""Remove blank lines that were inserted between decorators and the following def/class.

Usage: python3 scripts/fix_decorator_gaps.py <path>...
"""
from pathlib import Path
import sys


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = text.replace("\r\n", "\n")
    # Remove extra blank lines before decorators
    while "\n\n@" in text:
        text = text.replace("\n\n@", "\n@")
    # Also remove blank line between decorator and def if any remains
    text = text.replace("@\n\ndef", "@\ndef")
    text = text.replace("@\n\nclass", "@\nclass")
    if not text.endswith("\n"):
        text = text + "\n"
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fix_decorator_gaps.py <path> [<path> ...]")
        raise SystemExit(2)
    changed = []
    for p in sys.argv[1:]:
        root = Path(p)
        if root.is_dir():
            files = list(root.rglob("*.py"))
        elif root.endswith(".py"):
            files = [root]
        else:
            print(f"Skipping unknown path: {p}")
            continue
        for f in files:
            try:
                if fix_file(f):
                    changed.append(str(f))
            except Exception as e:
                print(f"Error processing {f}: {e}")
    print("Changed files:")
    for c in changed:
        print(" -", c)
