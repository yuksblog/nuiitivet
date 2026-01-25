#!/usr/bin/env python3
"""Safer blank-line fixer:
- Ensures top-level 'class' and 'def' have 2 blank lines before them.
- Does NOT insert extra blank lines between a decorator and its function/class.
- Operates on files recursively under given paths.
"""
from pathlib import Path
import sys


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    # Normalize newlines
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    out_lines = []
    i = 0
    L = len(lines)
    while i < L:
        line = lines[i]
        stripped = line.lstrip()
        is_top_def = (stripped.startswith("def ") or stripped.startswith("class ")) and (len(line) - len(stripped) == 0)
        if is_top_def:
            # Count preceding blank lines in out_lines
            prev_idx = len(out_lines) - 1
            blank_count = 0
            while prev_idx >= 0 and out_lines[prev_idx].strip() == "":
                blank_count += 1
                prev_idx -= 1
            # Check if previous non-blank line is a decorator
            prev_nonblank = out_lines[prev_idx] if prev_idx >= 0 else ""
            is_decorator = prev_nonblank.strip().startswith("@")
            if is_decorator:
                # Ensure exactly one blank line between decorator and def -> do nothing
                pass
            else:
                # Ensure at least two blank lines before top-level def/class
                need = 2 - blank_count
                if need > 0:
                    out_lines.extend([""] * need)
        out_lines.append(line)
        i += 1
    # Ensure final newline
    new_text = "\n".join(out_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    if new_text != orig:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fix_blanklines_safe.py <path> [<path> ...]")
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
