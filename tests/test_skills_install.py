"""Tests for ``nuiitivet.skills`` — installing the bundled agent skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from nuiitivet import skills


def test_available_skills_lists_the_bundled_skills() -> None:
    # In this checkout skills_root() falls back to the repository's skills/.
    names = skills.available_skills()
    assert "nuiitivet-app" in names
    assert "nuiitivet-debug" in names


def test_install_copies_skills_without_pycache(tmp_path: Path) -> None:
    dest = tmp_path / ".claude" / "skills"
    installed = skills.install(dest)

    assert dest / "nuiitivet-app" in installed
    assert (dest / "nuiitivet-app" / "SKILL.md").is_file()
    assert (dest / "nuiitivet-debug" / "SKILL.md").is_file()
    assert not list(dest.rglob("__pycache__"))
    assert not list(dest.rglob("*.pyc"))


def test_install_subset_installs_only_the_named_skill(tmp_path: Path) -> None:
    skills.install(tmp_path, names=["nuiitivet-debug"])
    assert (tmp_path / "nuiitivet-debug" / "SKILL.md").is_file()
    assert not (tmp_path / "nuiitivet-app").exists()


def test_install_replaces_an_existing_copy(tmp_path: Path) -> None:
    stale = tmp_path / "nuiitivet-app" / "stale.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("left over from an old version")

    skills.install(tmp_path, names=["nuiitivet-app"])

    assert not stale.exists()
    assert (tmp_path / "nuiitivet-app" / "SKILL.md").is_file()


def test_install_rejects_unknown_names(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no-such-skill"):
        skills.install(tmp_path, names=["no-such-skill"])
    assert not any(tmp_path.iterdir())


def test_cli_install_with_dest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from nuiitivet.skills.__main__ import main

    assert main(["install", "--dest", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "nuiitivet-app" in out
    assert (tmp_path / "nuiitivet-app" / "SKILL.md").is_file()


def test_cli_list_prints_skill_names(capsys: pytest.CaptureFixture[str]) -> None:
    from nuiitivet.skills.__main__ import main

    assert main(["list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "nuiitivet-app" in lines
    assert "nuiitivet-debug" in lines
