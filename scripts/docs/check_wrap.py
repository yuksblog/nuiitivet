"""Report Markdown lines that are not wrapped by their rendered width.

A link counts as its text: ``[text](url)`` takes the width of ``text``. Two
kinds of line are reported:

* a line that breaks early: it or the next line holds a link, and the next
  line's first word would still have fit. Such a break comes from counting
  the URL;
* a line that runs long: its rendered text is wider than ``--max``.

Fenced code, tables, headings, callout headers and images are skipped.

Run:  python scripts/docs/check_wrap.py [--width N] [--max N] FILE...

Exits 1 when a line is reported.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_LINK = re.compile(r"\[([^\]]*)\](?:\([^)]*\)|\[[^\]]*\])")
_FENCE = re.compile(r"^\s*(```|~~~)")
_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s")
_NOT_PROSE = ("#", "|", "!", "<", ">", "---")


def rendered(line: str) -> str:
    """The line as a reader sees it: each link replaced by its text."""
    return _LINK.sub(r"\1", line)


def _first_unit(line: str) -> str:
    """What a refill would move up first: a word, or a whole link with what is glued to it."""
    text = line.lstrip()
    link = _LINK.match(text)
    if link is None:
        return rendered(text).split()[0]
    glued = text[link.end() :].split(" ", 1)[0]
    return link.group(1) + rendered(glued)


def _is_prose(line: str) -> bool:
    text = line.strip()
    return bool(text) and not text.startswith(_NOT_PROSE)


def early_breaks(text: str, width: int) -> list[tuple[int, str, str]]:
    """The lines that break early, as ``(line number, line, the word that fits)``."""
    found: list[tuple[int, str, str]] = []
    lines = text.split("\n")
    in_fence = False
    for index, line in enumerate(lines[:-1]):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        following = lines[index + 1]
        if in_fence or not _is_prose(line) or not _is_prose(following):
            continue
        # The next line starts another list item or block: no paragraph to refill.
        if _ITEM.match(following) or _FENCE.match(following):
            continue
        if not (_LINK.search(line) or _LINK.search(following)):
            continue
        word = _first_unit(following)
        if len(rendered(line).rstrip()) + 1 + len(word) <= width:
            found.append((index + 1, line, word))
    return found


def long_lines(text: str, limit: int) -> list[tuple[int, str, int]]:
    """The prose lines whose rendered text is wider than ``limit``, as ``(line number, line, width)``."""
    found: list[tuple[int, str, int]] = []
    in_fence = False
    for index, line in enumerate(text.split("\n")):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or not _is_prose(line):
            continue
        width = len(rendered(line).rstrip())
        if width > limit:
            found.append((index + 1, line, width))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--width", type=int, default=76)
    parser.add_argument("--max", type=int, default=80)
    args = parser.parse_args()

    count = 0
    for path in args.files:
        text = path.read_text()
        for number, line, word in early_breaks(text, args.width):
            count += 1
            print(f"{path}:{number}: {word!r} fits on this line\n    {line}")
        for number, line, width in long_lines(text, args.max):
            count += 1
            print(f"{path}:{number}: {width} characters as rendered\n    {line}")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
