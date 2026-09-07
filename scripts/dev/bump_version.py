"""Bump the project version in every file that carries a copy of it.

    uv run python scripts/dev/bump_version.py 0.22.0

Three files have to agree. ``pyproject.toml`` is the source of truth, ``uv.lock``
keeps its own copy that CI's ``uv sync --locked`` refuses to work around, and the
Claude Code plugin manifest ships the same number to plugin users. Bumping one
and forgetting another is the failure this script exists to make impossible.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
LOCK = ROOT / "uv.lock"

# Deliberately narrower than PEP 440: this project releases X.Y.Z and the
# occasional pre-release, and a typo'd version cannot be taken back off PyPI.
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?$")

_TOML_VERSION = re.compile(r'^version = "([^"]*)"$', re.MULTILINE)
_JSON_VERSION = re.compile(r'^(?P<lead>\s*"version":\s*)"(?P<value>[^"]*)"', re.MULTILINE)
_TOML_TABLE = re.compile(r"^\[", re.MULTILINE)
_LOCK_PACKAGE = re.compile(r"^\[\[package\]\]$", re.MULTILINE)


def _project_table(text: str) -> tuple[int, int]:
    """Return the [project] table's span, so sibling tables' keys stay untouched."""
    header = re.search(r"^\[project\]$", text, re.MULTILINE)
    if header is None:
        raise LookupError("pyproject.toml has no [project] table")
    following = _TOML_TABLE.search(text, header.end())
    return header.end(), following.start() if following else len(text)


def read_pyproject_version(text: str) -> str:
    """Read ``project.version`` out of pyproject.toml's source."""
    start, end = _project_table(text)
    match = _TOML_VERSION.search(text, start, end)
    if match is None:
        raise LookupError("pyproject.toml's [project] table has no version")
    return match.group(1)


def read_plugin_version(text: str) -> str:
    """Read the version out of the plugin manifest's source."""
    match = _JSON_VERSION.search(text)
    if match is None:
        raise LookupError("plugin.json has no version")
    return match.group("value")


def read_lock_version(text: str) -> str:
    """Read the version uv.lock records for this project's own package."""
    for package in _LOCK_PACKAGE.finditer(text):
        following = _LOCK_PACKAGE.search(text, package.end())
        block = text[package.end(): following.start() if following else len(text)]
        if re.search(r'^name = "nuiitivet"$', block, re.MULTILINE) is None:
            continue
        match = _TOML_VERSION.search(block)
        if match is None:
            raise LookupError("uv.lock's nuiitivet package has no version")
        return match.group(1)
    raise LookupError("uv.lock has no nuiitivet package")


def current_versions() -> dict[Path, str]:
    """Read the version each of the three files currently carries."""
    return {
        PYPROJECT: read_pyproject_version(PYPROJECT.read_text(encoding="utf-8")),
        PLUGIN: read_plugin_version(PLUGIN.read_text(encoding="utf-8")),
        LOCK: read_lock_version(LOCK.read_text(encoding="utf-8")),
    }


def _write_pyproject(version: str) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    start, end = _project_table(text)
    match = _TOML_VERSION.search(text, start, end)
    if match is None:
        raise LookupError("pyproject.toml's [project] table has no version")
    PYPROJECT.write_text(text[:match.start(1)] + version + text[match.end(1):], encoding="utf-8")


def _write_plugin(version: str) -> None:
    # Rewriting the one line rather than re-serialising the file keeps the
    # manifest's formatting and key order out of this script's hands.
    text = PLUGIN.read_text(encoding="utf-8")
    match = _JSON_VERSION.search(text)
    if match is None:
        raise LookupError("plugin.json has no version")
    PLUGIN.write_text(text[:match.start("value")] + version + text[match.end("value"):], encoding="utf-8")


def bump(version: str) -> None:
    """Write the version to all three files, then verify they agree."""
    _write_pyproject(version)
    _write_plugin(version)
    subprocess.run(["uv", "lock"], cwd=ROOT, check=True)

    disagree = {path: found for path, found in current_versions().items() if found != version}
    if disagree:
        raise SystemExit(
            "the bump did not land everywhere:\n"
            + "\n".join(f"  {path.relative_to(ROOT)}: {found}" for path, found in disagree.items())
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bump the project version across pyproject, uv.lock and plugin.json.")
    parser.add_argument("version", nargs="?", help="the new version, e.g. 0.22.0")
    parser.add_argument("--check", action="store_true", help="report the current versions instead of bumping")
    args = parser.parse_args(argv)

    if args.check:
        versions = current_versions()
        for path, found in versions.items():
            print(f"{path.relative_to(ROOT)}: {found}")
        return 0 if len(set(versions.values())) == 1 else 1

    if args.version is None:
        parser.error("a version is required unless --check is given")
    if VERSION.match(args.version) is None:
        parser.error(f"{args.version!r} is not a version this project releases (X.Y.Z, or X.Y.Zrc1)")

    bump(args.version)
    print(f"bumped to {args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
