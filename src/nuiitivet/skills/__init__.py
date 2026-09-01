"""Install the agent skills bundled with nuiitivet.

The framework ships its Claude Code skills (``nuiitivet-app``,
``nuiitivet-debug``) inside the wheel as ``nuiitivet/_skills_data/`` (see
``setup.py``), so the skills a user installs always match the framework
version they have. ``python -m nuiitivet.skills install`` copies them into a
Claude Code skills directory; re-run it after upgrading nuiitivet to update
them.
"""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path
from typing import Optional, Sequence


def skills_root() -> Path:
    """Return the directory holding the bundled skill sources.

    A wheel install carries them as ``nuiitivet/_skills_data/``; an editable or
    repo checkout (where the build hook never ran) falls back to the repository's
    ``skills/`` tree.

    Raises:
        FileNotFoundError: If neither location exists.
    """
    bundled = Path(str(resources.files("nuiitivet"))) / "_skills_data"
    if bundled.is_dir():
        return bundled
    repo = Path(__file__).resolve().parents[3] / "skills"
    if repo.is_dir():
        return repo
    raise FileNotFoundError(
        "Bundled skills not found: neither the packaged 'nuiitivet/_skills_data' "
        "nor a repository 'skills/' directory exists."
    )


def available_skills() -> list[str]:
    """Return the names of the bundled skills, sorted.

    A skill is any direct subdirectory of :func:`skills_root` that contains a
    ``SKILL.md``.
    """
    return sorted(
        entry.name for entry in skills_root().iterdir() if (entry / "SKILL.md").is_file()
    )


def install(dest: Path, *, names: Optional[Sequence[str]] = None) -> list[Path]:
    """Copy the bundled skills into ``dest``, replacing existing copies.

    Args:
        dest: Target skills directory (e.g. ``.claude/skills``). Created if
            missing.
        names: Skills to install; defaults to every bundled skill.

    Returns:
        The paths of the installed skill directories.

    Raises:
        ValueError: If ``names`` contains a name that is not bundled.
    """
    root = skills_root()
    bundled = available_skills()
    selected = list(names) if names is not None else bundled
    unknown = sorted(set(selected) - set(bundled))
    if unknown:
        raise ValueError(
            f"Unknown skill(s): {', '.join(unknown)}. Bundled: {', '.join(bundled)}."
        )

    dest.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    for name in selected:
        target = dest / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(
            root / name,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.py[cod]"),
        )
        installed.append(target)
    return installed
