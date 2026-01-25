#!/usr/bin/env python3
"""Normalize decorator spacing.

Combined fixer to:
- Remove extra blank lines before decorator chains.
- Remove blank lines between a decorator (or decorator chain) and the following
  `def`/`class`.

This merges the behavior of `fix_decorator_followers.py` and
`fix_decorator_gaps.py` into a single utility.
"""
from pathlib import Path
import sys
import re


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = text.replace("\r\n", "\n")
    # Remove extra blank lines before decorators
    text = re.sub(r"\n\n+@", "\n@", text)
    # Remove blank line(s) between decorator and def/class
    text = text.replace("@\n\ndef", "@\ndef")
    text = text.replace("@\n\nclass", "@\nclass")
    # Also remove any remaining double-newline directly before decorator
    text = re.sub(r"\n\n+@", "\n@", text)
    if not text.endswith("\n"):
        text += "\n"
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fix_decorators.py <path> [<path> ...]")
        raise SystemExit(2)
    changed = []
    for p in sys.argv[1:]:
        root = Path(p)
        if root.is_dir():
            files = list(root.rglob("*.py"))
        elif p.endswith(".py"):
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
