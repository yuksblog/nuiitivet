"""Reload the user's modules on save (§9.6 / §9.8 of HOT_RELOAD.md).

Two concerns live here:

- **Identification (§9.8):** decide which loaded modules are the *user's* and are
  therefore safe to reload. ``nuiitivet``, ``skia`` and ``pyglet`` are never
  reloaded (they wrap C extensions); this is enforced by both a name blacklist
  and a "file must live under the project root" check.

- **Ordering (§9.6, case 1):** reload user modules in dependency order — a
  depended-upon module (a leaf like ``widgets``) before its dependents (``app``)
  — so that after reloading, a dependent's ``from .widgets import W`` re-binds to
  the *new* class object instead of固着 to the stale one.

All user modules are reloaded on every change (not just the saved file): reloading
only the saved leaf would leave dependents holding stale bindings. Restoring
in-tree ``Observable`` state is handled separately by the snapshot module;
module-level state is intentionally out of scope (§9.5).
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Top-level packages that must never be reloaded. ``skia``/``pyglet`` wrap C
# extensions; ``nuiitivet`` is the framework itself. This is the hard safety net
# required by #359 regardless of where the files happen to live.
_BLACKLIST_ROOTS = frozenset({"nuiitivet", "skia", "skia_python", "pyglet"})


@dataclass
class ReloadResult:
    """Outcome of a reload pass."""

    reloaded: list[str] = field(default_factory=list)
    """Names of modules that were reloaded, in the order applied."""
    new_factory: Optional[Callable[[], object]] = None
    """The root factory re-fetched from its (reloaded) module, or ``None`` when it
    could not be re-fetched (anonymous/local factory). ``None`` means the caller
    should keep the existing factory; internal widget changes still take effect."""


def _is_user_module(module: ModuleType, project_root: Path) -> bool:
    """True if ``module`` is one of the user's, safe to reload."""
    name = getattr(module, "__name__", "")
    if not name:
        return False
    root_pkg = name.split(".", 1)[0]
    if root_pkg in _BLACKLIST_ROOTS:
        return False

    file = getattr(module, "__file__", None)
    if not file:
        # Built-in / namespace / C-extension modules have no reloadable source.
        return False
    try:
        resolved = Path(file).resolve()
    except Exception:
        return False
    try:
        resolved.relative_to(project_root)
    except ValueError:
        # Outside the project root (e.g. site-packages, stdlib): not user code.
        return False
    return True


def identify_user_modules(project_root: Path) -> dict[str, ModuleType]:
    """Return the currently-loaded user modules keyed by name (§9.8)."""
    project_root = project_root.resolve()
    result: dict[str, ModuleType] = {}
    for name, module in list(sys.modules.items()):
        if module is None:
            continue
        if _is_user_module(module, project_root):
            result[name] = module
    return result


def _module_dependencies(module: ModuleType, user_names: set[str]) -> set[str]:
    """Approximate the user modules ``module`` depends on.

    Inspects the module's globals: an imported submodule object, or an imported
    class/function whose ``__module__`` is another user module, both indicate a
    dependency. Good enough to order ``from .widgets import W`` before its users.
    """
    deps: set[str] = set()
    self_name = getattr(module, "__name__", "")
    for value in list(vars(module).values()):
        if isinstance(value, ModuleType):
            dep = getattr(value, "__name__", None)
        else:
            dep = getattr(value, "__module__", None)
        if dep and dep != self_name and dep in user_names:
            deps.add(dep)
    return deps


def _topological_order(modules: dict[str, ModuleType]) -> list[str]:
    """Order module names dependencies-first (leaves before dependents).

    Uses DFS post-order. Import cycles are broken arbitrarily (best effort); the
    result is still a total order so every module is reloaded exactly once.
    """
    user_names = set(modules)
    deps = {name: _module_dependencies(mod, user_names) for name, mod in modules.items()}

    ordered: list[str] = []
    visited: set[str] = set()
    on_stack: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        on_stack.add(name)
        for dep in sorted(deps.get(name, ())):
            if dep in on_stack:
                # Cycle: skip this edge to avoid infinite recursion.
                continue
            visit(dep)
        on_stack.discard(name)
        ordered.append(name)

    for name in sorted(modules):
        visit(name)
    return ordered


def _refetch_factory(
    old_factory: Callable[[], object],
) -> Optional[Callable[[], object]]:
    """Re-fetch the root factory from its reloaded module by name (§9.1).

    A module-level named function or class can be re-resolved after reload so that
    changes to the *factory definition itself* (not just the widgets it builds)
    are picked up. Anonymous (``lambda``) or locally-defined factories cannot be
    re-fetched; ``None`` is returned and the caller keeps the existing factory.
    """
    mod_name = getattr(old_factory, "__module__", None)
    qualname = getattr(old_factory, "__qualname__", getattr(old_factory, "__name__", ""))
    if not mod_name or not qualname:
        return None
    if "<locals>" in qualname or "<lambda>" in qualname:
        return None
    module = sys.modules.get(mod_name)
    if module is None:
        return None
    obj = getattr(module, qualname.split(".", 1)[0], None)
    return obj if callable(obj) else None


def reload_user_modules(
    project_root: Path,
    old_factory: Optional[Callable[[], object]] = None,
) -> ReloadResult:
    """Reload all user modules in dependency order and re-fetch the factory.

    Args:
        project_root: Root under which user modules live (from the loader).
        old_factory: The current root factory, re-fetched from its reloaded
            module when possible.

    Returns:
        A :class:`ReloadResult`.
    """
    modules = identify_user_modules(project_root)
    order = _topological_order(modules)

    # Drop stale finder/bytecode caches. ``importlib.reload`` recompiles from
    # source only when it decides the cached ``.pyc`` is out of date, and that
    # check uses second-granularity mtimes — a save in the same wall-clock second
    # as the last compile can be missed, reloading stale bytecode. Removing the
    # user modules' ``.pyc`` files forces a fresh compile from the edited source.
    importlib.invalidate_caches()
    for name in order:
        module = sys.modules.get(name)
        source = getattr(module, "__file__", None) if module is not None else None
        if not source:
            continue
        try:
            os.remove(importlib.util.cache_from_source(source))
        except (OSError, ValueError, NotImplementedError):
            pass

    result = ReloadResult()
    for name in order:
        module = sys.modules.get(name)
        if module is None:
            continue
        importlib.reload(module)
        result.reloaded.append(name)

    if old_factory is not None:
        result.new_factory = _refetch_factory(old_factory)

    logger.debug("hot reload: reloaded %d module(s): %s", len(result.reloaded), result.reloaded)
    return result
