#!/usr/bin/env python3
"""Final pass fixer:
- Ensure two blank lines before top-level `class`/`def` and top-level decorators.
- Avoid inserting blank lines between decorator chain and the following `def`/`class`.
"""
from pathlib import Path
import sys


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    out = []
    i = 0
    L = len(lines)
    while i < L:
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        is_top_def = (indent == 0) and (stripped.startswith("def ") or stripped.startswith("class "))
        is_top_decorator = (indent == 0) and stripped.startswith("@")
        if is_top_decorator:
            # check prev non-blank line
            prev_idx = len(out) - 1
            blank_count = 0
            while prev_idx >= 0 and out[prev_idx].strip() == "":
                blank_count += 1
                prev_idx -= 1
            # If prev non-blank is decorator, it's part of chain -> ensure one blank line only before chain
            prev_nonblank = out[prev_idx] if prev_idx >= 0 else ""
            if prev_nonblank.strip().startswith("@"):
                # already in decorator chain, do nothing
                pass
            else:
                need = 2 - blank_count
                if need > 0:
                    out.extend([""] * need)
        elif is_top_def:
            prev_idx = len(out) - 1
            blank_count = 0
            while prev_idx >= 0 and out[prev_idx].strip() == "":
                blank_count += 1
                prev_idx -= 1
            prev_nonblank = out[prev_idx] if prev_idx >= 0 else ""
            # If previous nonblank is decorator, skip (decorator handles spacing)
            if prev_nonblank.strip().startswith("@"):
                pass
            else:
                need = 2 - blank_count
                if need > 0:
                    out.extend([""] * need)
        out.append(line)
        i += 1
    new_text = "\n".join(out)
    if not new_text.endswith("\n"):
        new_text += "\n"
    if new_text != orig:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fix_blanklines_final.py <path> [<path> ...]")
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
