#!/usr/bin/env python3
"""Remove blank lines between a decorator and the following def/class.

Replaces patterns like:
    @decorator\n\nclass Foo:
with
    @decorator\nclass Foo:
"""
from pathlib import Path
import sys


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = text.replace("\r\n", "\n")
    # Collapse decorator followed by an extra blank line before def/class
    import re

    text = re.sub(r"(@[^\n]+)\n\n(class|def)\b", r"\1\n\2", text)
    if not text.endswith("\n"):
        text += "\n"
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fix_decorator_followers.py <path> [<path> ...]")
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
