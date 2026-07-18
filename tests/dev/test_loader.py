"""Tests for dev-runner root resolution (``find_discovery_root``)."""

from __future__ import annotations

from pathlib import Path

from nuiitivet.dev.loader import find_discovery_root


def test_returns_import_root_when_it_holds_a_marker(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    assert find_discovery_root(tmp_path, env={}) == tmp_path.resolve()


def test_ascends_to_nearest_project_marker(tmp_path: Path) -> None:
    # Repo root has .git; a nested bare-script dir has no marker of its own.
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "samples" / "advanced"
    nested.mkdir(parents=True)
    # A bare script imports from its own directory (the import root), which sits
    # below the repo root -- the anchor must climb to where .git lives.
    assert find_discovery_root(nested, env={}) == tmp_path.resolve()


def test_prefers_nearest_marker_in_monorepo(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    package = tmp_path / "packages" / "app"
    package.mkdir(parents=True)
    (package / "pyproject.toml").write_text("", encoding="utf-8")
    # The package boundary (nearest marker) wins over the outer repo root.
    assert find_discovery_root(package, env={}) == package.resolve()


def test_git_marker_may_be_a_file(tmp_path: Path) -> None:
    # git worktrees record .git as a file, not a directory.
    (tmp_path / ".git").write_text("gitdir: /elsewhere", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    assert find_discovery_root(nested, env={}) == tmp_path.resolve()


def test_falls_back_to_import_root_without_marker(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    # No marker anywhere: the import root is used unchanged.
    assert find_discovery_root(nested, env={}) == nested.resolve()


def test_env_override_wins(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    override = tmp_path / "chosen"
    override.mkdir()
    result = find_discovery_root(tmp_path, env={"NUIITIVET_DEV_ROOT": str(override)})
    assert result == override.resolve()


def test_env_override_ignored_when_not_a_directory(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    missing = tmp_path / "does-not-exist"
    # A bogus override is ignored; resolution falls through to the marker search.
    result = find_discovery_root(tmp_path, env={"NUIITIVET_DEV_ROOT": str(missing)})
    assert result == tmp_path.resolve()
