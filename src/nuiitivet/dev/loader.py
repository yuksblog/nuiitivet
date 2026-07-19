"""Load the user's app module for the dev runner (§9.7 of HOT_RELOAD.md).

The dev runner accepts either a **file path** (matching the documented
``launch.json`` ``args: ["${workspaceFolder}/app.py"]``) or an explicit
**module name** (``--module yourpkg.app``). Either way the module must be
imported under a *stable, real* name — never ``__main__`` — so that:

- ``importlib.reload`` can re-run it (reload needs a name in ``sys.modules``);
- relative imports inside it (``from .widgets import ...``) resolve correctly.

For a path we recover the dotted module name by walking up the directory tree as
long as ``__init__.py`` files are present, so ``pkg/sub/app.py`` in a package
becomes ``pkg.sub.app`` and a bare script becomes its file stem. The package
root's parent is placed on ``sys.path`` so the import resolves.
"""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional

# Environment override for the dev-bridge discovery anchor (see
# :func:`find_discovery_root`).
_DISCOVERY_ROOT_ENV = "NUIITIVET_DEV_ROOT"

# Files that mark the root of a user-facing project. Searched nearest-first so
# the most specific boundary wins (a package in a monorepo over the repo root).
# ``.git`` may be a file (git worktrees), so existence -- not is-dir -- is checked.
_PROJECT_MARKERS = (".git", "pyproject.toml", ".hg", "setup.py", "setup.cfg")


@dataclass(frozen=True)
class LoadedApp:
    """Result of loading the user's app entry module."""

    module: ModuleType
    """The imported user module (registered in ``sys.modules`` under ``name``)."""
    name: str
    """The dotted module name the module is registered under."""
    project_root: Path
    """Directory added to ``sys.path`` to import the module. Anchors user-module
    identification during reload (§9.8): modules whose files live under this
    root are candidates for reload."""


def _derive_module_name(file_path: Path) -> tuple[str, Path]:
    """Recover a dotted module name and the sys.path entry for a file path.

    Walks up through parent directories that contain ``__init__.py`` to rebuild
    the package-relative dotted name. Returns ``(module_name, sys_path_entry)``
    where importing ``module_name`` after inserting ``sys_path_entry`` on
    ``sys.path`` loads the file with correct package context.
    """
    file_path = file_path.resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"App file not found: {file_path}")
    if file_path.is_dir():
        raise IsADirectoryError(f"Expected a .py file, got a directory: {file_path}")

    if file_path.name == "__init__.py":
        # Importing a package's __init__.py means importing the package itself.
        parts = [file_path.parent.name]
        root = file_path.parent.parent
    else:
        parts = [file_path.stem]
        root = file_path.parent

    # Ascend while each directory is a package, prepending its name.
    while (root / "__init__.py").exists():
        parts.insert(0, root.name)
        root = root.parent

    return ".".join(parts), root


def load_app_module(target: str, *, is_module: bool) -> LoadedApp:
    """Import the user's app module under a stable, reloadable name.

    Args:
        target: A file path (``is_module=False``) or a dotted module name
            (``is_module=True``).
        is_module: Whether ``target`` is a module name rather than a path.

    Returns:
        A :class:`LoadedApp` describing the imported module.

    Raises:
        FileNotFoundError / IsADirectoryError: For an invalid path target.
        ModuleNotFoundError: If the module cannot be imported.
    """
    if is_module:
        module_name = target
        # ``python -m`` already places cwd on sys.path; the project root for
        # user-module identification is the cwd in this mode.
        project_root = Path.cwd().resolve()
    else:
        module_name, sys_path_entry = _derive_module_name(Path(target))
        project_root = sys_path_entry
        entry = str(sys_path_entry)
        if entry not in sys.path:
            sys.path.insert(0, entry)

    module = importlib.import_module(module_name)
    return LoadedApp(module=module, name=module_name, project_root=project_root)


def find_discovery_root(import_root: Path, *, env: Optional[dict[str, str]] = None) -> Path:
    """Anchor for the dev-bridge discovery file, decoupled from the import root.

    The discovery file must live where a client can find it by searching *upward*
    from its cwd (like ``git`` finding ``.git``). Python's import root -- the
    ``sys.path`` entry a module loads from -- is the wrong anchor for this: a
    nested bare script (``examples/demo/app.py`` with no ``__init__.py``)
    imports from its own directory, so the file would land *below* the project
    root and an upward search from there would never reach it.

    The anchor is resolved, in order:

    1. the ``NUIITIVET_DEV_ROOT`` environment variable, if it names a directory;
    2. the nearest ancestor of ``import_root`` (inclusive) holding a project
       marker (``.git`` / ``pyproject.toml`` / ...), so the file lands at the
       user-facing project root;
    3. ``import_root`` itself, unchanged, when no marker is found.

    The common packaged-app case (an ``app.py`` at the workspace root) already
    has ``import_root`` == the workspace root, so this returns it either way --
    behavior there is identical to anchoring on the import root directly.
    """
    environ = os.environ if env is None else env
    override = environ.get(_DISCOVERY_ROOT_ENV)
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_dir():
            return candidate.resolve()

    import_root = import_root.resolve()
    for directory in (import_root, *import_root.parents):
        if any((directory / marker).exists() for marker in _PROJECT_MARKERS):
            return directory
    return import_root


def resolve_entry(module: ModuleType, entry_name: str = "main") -> Callable[[], object]:
    """Return the user's entry callable (default ``main``) from ``module``.

    Raises:
        AttributeError: If no such attribute exists.
        TypeError: If the attribute is not callable.
    """
    if not hasattr(module, entry_name):
        raise AttributeError(
            f"Module '{module.__name__}' has no '{entry_name}()' entry point. "
            f"Define a '{entry_name}()' function that builds and runs the App, "
            f"or pass --entry <name>."
        )
    entry = getattr(module, entry_name)
    if not callable(entry):
        raise TypeError(f"'{module.__name__}.{entry_name}' is not callable.")
    return entry
