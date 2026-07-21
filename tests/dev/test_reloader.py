"""Tests for user-module identification in the hot-reload reloader (#422).

The reloader must reload only the user's in-tree modules. The regression these
tests guard against is a project-local ``.venv/`` (``uv``'s default): when
site-packages lives *inside* the project root, dependencies resolve under the
project root and were misclassified as user code, then reloaded on every save --
corrupting C-extension state (PyOpenGL crashed the whole reload pass).
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Optional
from unittest import mock

from nuiitivet.dev import reloader as reloader_mod
from nuiitivet.dev.reloader import _is_user_module, identify_user_modules


def _fake_module(name: str, file: Optional[str]) -> ModuleType:
    """A module object with just the attributes ``_is_user_module`` reads."""
    module = ModuleType(name)
    if file is not None:
        module.__file__ = file
    return module


def _is_user(module: ModuleType, project_root: Path, site_dirs: tuple[Path, ...]) -> bool:
    with mock.patch.object(reloader_mod, "_site_directories", return_value=site_dirs):
        return _is_user_module(module, project_root.resolve())


def test_site_packages_inside_project_root_is_rejected(tmp_path: Path) -> None:
    """A project-local ``.venv`` dependency is not user code, despite living
    under the project root (the #422 regression)."""
    project_root = tmp_path
    site_dir = project_root / ".venv" / "Lib" / "site-packages"
    dep = _fake_module("OpenGL.platform", str(site_dir / "OpenGL" / "platform.py"))

    assert not _is_user(dep, project_root, (site_dir,))


def test_in_tree_user_module_is_reloadable(tmp_path: Path) -> None:
    """Source under the project root but outside any site dir stays user code."""
    project_root = tmp_path
    site_dir = project_root / ".venv" / "Lib" / "site-packages"
    app = _fake_module("app", str(project_root / "src" / "app.py"))

    assert _is_user(app, project_root, (site_dir,))


def test_editable_install_in_tree_stays_reloadable(tmp_path: Path) -> None:
    """``pip install -e`` source in the tree is genuinely the user's code."""
    project_root = tmp_path
    site_dir = project_root / ".venv" / "Lib" / "site-packages"
    pkg = _fake_module("mypkg.core", str(project_root / "mypkg" / "core.py"))

    assert _is_user(pkg, project_root, (site_dir,))


def test_blacklist_root_is_rejected(tmp_path: Path) -> None:
    """Blacklisted roots are never reloaded even from in-tree source."""
    project_root = tmp_path
    nuiitivet = _fake_module("nuiitivet.widgets", str(project_root / "nuiitivet" / "widgets.py"))

    assert not _is_user(nuiitivet, project_root, ())


def test_module_without_file_is_rejected(tmp_path: Path) -> None:
    """Built-in / namespace / C-extension modules have no reloadable source."""
    builtin = _fake_module("sys", None)

    assert not _is_user(builtin, tmp_path, ())


def test_site_packages_outside_project_root_is_rejected(tmp_path: Path) -> None:
    """The classic layout (site-packages outside the tree) still excludes deps."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    site_dir = tmp_path / "venv" / "site-packages"
    dep = _fake_module("numpy", str(site_dir / "numpy" / "__init__.py"))

    assert not _is_user(dep, project_root, (site_dir,))


def test_identify_user_modules_excludes_project_local_site_packages(tmp_path: Path) -> None:
    """End-to-end: identification skips a dependency in a project-local venv."""
    project_root = tmp_path
    site_dir = project_root / ".venv" / "Lib" / "site-packages"
    app = _fake_module("app", str(project_root / "app.py"))
    dep = _fake_module("OpenGL", str(site_dir / "OpenGL" / "__init__.py"))

    fake_sys_modules = {"app": app, "OpenGL": dep}
    with mock.patch.object(reloader_mod, "_site_directories", return_value=(site_dir,)):
        with mock.patch.object(reloader_mod.sys, "modules", fake_sys_modules):
            user = identify_user_modules(project_root)

    assert set(user) == {"app"}
