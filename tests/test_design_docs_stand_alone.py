"""Design docs stand alone: no pointer at the guide, no issue number.

``docs/design/`` is not part of the built site, so nothing verifies a pointer
from there into ``docs/guide/``. A guide page that is renamed or split leaves
it wrong with no signal. Links between design docs are left alone: they are
the same kind of document and move together.

An issue number is a pointer the reader cannot follow from the page, and the
sentence around it usually tells how the design was reached instead of what it
is. The design doc states the decision; tracking lives in the issue and the PR.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESIGN_ROOT = PROJECT_ROOT / "docs" / "design"

# A guide page named by path. The relative link target and the prose spelling
# from the repository root both end in "guide/<path>.md".
GUIDE_REF = re.compile(r"guide/[\w./-]+\.md")

# An issue-number citation: "#" glued to 2-5 digits.
ISSUE_REF = re.compile(r"#\d{2,5}\b")

# A Markdown link target carrying an anchor, in this page or in another design
# doc, is navigation, not a citation.
MD_ANCHOR = re.compile(r"\]\([\w./-]*#[\w-]+\)")


def _violations(pattern: re.Pattern[str], *, ignore: re.Pattern[str] | None = None) -> list[str]:
    files = sorted(DESIGN_ROOT.rglob("*.md"))
    assert files, f"no design docs found under {DESIGN_ROOT}"
    found: list[str] = []
    for path in files:
        relative = path.relative_to(PROJECT_ROOT)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = pattern.search(ignore.sub("", line) if ignore else line)
            if match:
                found.append(f"{relative}:{number}: {match.group(0)!r}: {line.strip()}")
    return found


def test_design_docs_do_not_point_at_the_guide() -> None:
    violations = _violations(GUIDE_REF)
    assert not violations, "A design doc does not point at the guide -- name the topic, not the page:\n" + "\n".join(
        violations
    )


def test_design_docs_carry_no_issue_numbers() -> None:
    violations = _violations(ISSUE_REF, ignore=MD_ANCHOR)
    assert not violations, "A design doc carries no issue number -- state the design, not its tracker:\n" + "\n".join(
        violations
    )
