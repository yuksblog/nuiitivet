"""Comments must stand alone: no issue numbers, no design-doc links.

A comment whose meaning depends on an issue number is a comment that has not
been written yet -- the fix is to say the thing, not to cite where it was
said. A link to an in-tree document rots with no signal: nothing verifies the
target still exists or still says what the comment claims. Full reasoning is
recoverable without either, because this repository writes explanatory commit
messages that ``git blame`` and ``git log -S`` reach from any line.

This test enforces the rule over the tree's own source: ``src/``, ``tests/``,
``samples/``, and the published skill content under ``skills/``. It scans
whole files rather than parsing comments out, so a violating string literal
(an error message citing an issue) is caught too -- a runtime message is just
as unable to resolve a tracker number as a comment is.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCAN_ROOTS = ("src", "tests", "samples", "skills")
SCAN_SUFFIXES = {".py", ".md"}

# Directories that hold generated or vendored content, not authored source.
EXCLUDED_DIR_NAMES = {".venv", "__pycache__", "nuiitivet.egg-info"}

# An issue-number citation: "#" glued to 2-5 digits ("#591", "#36").
# Anything shorter is a heading level or a list marker; anything longer is
# not a tracker number this project could have issued.
ISSUE_REF = re.compile(r"#\d{2,5}\b")

# A pointer into the in-tree documentation: an explicit docs/ path, or a
# bare SCREAMING_CASE design-doc name ("HOT_RELOAD.md").
DOC_REF = re.compile(r"docs/(?:design|guide|md3)/[\w./-]+\.md|\b[A-Z][A-Z_]+\.md\b")

# Lines allowed to contain what looks like a violation:
# - a quoted hex color ("#666", "#RRGGBB") is a value, not a citation;
# - a Markdown intra-page anchor ("](#21-section-title)") is navigation.
HEX_COLOR = re.compile(r"""["']#[0-9a-fA-F]{3,8}["']""")
MD_ANCHOR = re.compile(r"\]\(#[\w-]+\)")

# File names that are an on-disk contract, not a document citation: the
# skills loader looks for a literal SKILL.md next to each skill.
ALLOWED_NAMES = ("SKILL.md",)

# This file legitimately names the patterns it hunts.
SELF = Path(__file__).name


def _scan_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        base = PROJECT_ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in SCAN_SUFFIXES or not path.is_file():
                continue
            if EXCLUDED_DIR_NAMES.intersection(path.parts):
                continue
            if path.name == SELF:
                continue
            files.append(path)
    return files


def _violations_in(path: Path) -> list[str]:
    found: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = HEX_COLOR.sub("", MD_ANCHOR.sub("", line))
        for name in ALLOWED_NAMES:
            stripped = stripped.replace(name, "")
        for pattern, kind in ((ISSUE_REF, "issue number"), (DOC_REF, "doc link")):
            match = pattern.search(stripped)
            if match:
                relative = path.relative_to(PROJECT_ROOT)
                found.append(f"{relative}:{number}: {kind} {match.group(0)!r}: {line.strip()}")
    return found


def test_no_issue_numbers_or_doc_links_in_source() -> None:
    violations = [entry for path in _scan_files() for entry in _violations_in(path)]
    assert not violations, (
        "Comments must stand alone -- state the fact instead of citing an "
        "issue number or a document:\n" + "\n".join(violations)
    )
