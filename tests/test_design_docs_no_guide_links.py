"""Design docs must not point at the guide: no link, no path in prose.

``docs/design/`` is not part of the built site, so nothing verifies a pointer
from there into ``docs/guide/``. A guide page that is renamed or split leaves
it wrong with no signal. Links between design docs are left alone: they are
the same kind of document and move together.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESIGN_ROOT = PROJECT_ROOT / "docs" / "design"

# A guide page named by path. The relative link target and the prose spelling
# from the repository root both end in "guide/<path>.md".
GUIDE_REF = re.compile(r"guide/[\w./-]+\.md")


def _violations_in(path: Path) -> list[str]:
    found: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = GUIDE_REF.search(line)
        if match:
            relative = path.relative_to(PROJECT_ROOT)
            found.append(f"{relative}:{number}: {match.group(0)!r}: {line.strip()}")
    return found


def test_design_docs_do_not_point_at_the_guide() -> None:
    files = sorted(DESIGN_ROOT.rglob("*.md"))
    assert files, f"no design docs found under {DESIGN_ROOT}"
    violations = [entry for path in files for entry in _violations_in(path)]
    assert not violations, "A design doc does not point at the guide -- name the topic, not the page:\n" + "\n".join(
        violations
    )
