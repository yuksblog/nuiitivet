"""Apply a save to the running app's modules.

A saved module whose source differs from the one it ran with only inside def
bodies is patched in place. Any other saved module is re-executed, and so is
every user module that imports it.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import logging
import os
import site
import sys
import sysconfig
import threading
import weakref
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional

from .patcher import Unpatchable, patch_bodies, runs_source

logger = logging.getLogger(__name__)

# Top-level packages that must never be reloaded. ``skia``/``pyglet`` wrap C
# extensions; ``nuiitivet`` is the framework itself. This is the hard safety net
# that holds regardless of where the files happen to live.
_BLACKLIST_ROOTS = frozenset({"nuiitivet", "skia", "skia_python", "pyglet"})


@lru_cache(maxsize=1)
def _site_directories() -> tuple[Path, ...]:
    """Resolved install directories where dependencies live.

    Third-party and stdlib packages install under the interpreter's site
    directories. When the virtualenv lives *inside* the project root (e.g.
    ``uv``'s default project-local ``.venv/``), those directories are under
    ``project_root``, so the plain "file is under project_root" check
    misclassifies every dependency as reloadable user code. Rejecting anything
    under a real site directory fixes that independently of the package manager
    and without guessing from folder names.

    Combines ``sysconfig`` (``purelib``/``platlib``) with ``site``
    (``getsitepackages()`` + the per-user site for ``pip install --user``).
    """
    candidates: list[str] = []
    paths = sysconfig.get_paths()
    for key in ("purelib", "platlib", "stdlib", "platstdlib"):
        path = paths.get(key)
        if path:
            candidates.append(path)
    # ``getsitepackages`` is absent in some virtualenvs; guard it.
    getsitepackages = getattr(site, "getsitepackages", None)
    if getsitepackages is not None:
        try:
            candidates.extend(getsitepackages())
        except Exception:
            pass
    try:
        candidates.append(site.getusersitepackages())
    except Exception:
        pass

    resolved: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved_path = Path(candidate).resolve()
        except Exception:
            continue
        if resolved_path not in seen:
            seen.add(resolved_path)
            resolved.append(resolved_path)
    return tuple(resolved)


@dataclass
class ReloadResult:
    """What one save did to the user's modules.

    Attributes:
        changed: The modules whose source differs from the one they ran with.
        patched: The modules whose living functions took new code.
        reloaded: The modules re-executed, in the order applied.
        edited: The re-executed modules whose own source changed. The others
            were re-executed for importing one of them.
        replaced: Per re-executed module, the classes it defined before, as weak references.
        new_factory: The root factory re-fetched from its module, or ``None``
            for a lambda or a local function, which the caller keeps.
    """

    changed: list[str] = field(default_factory=list)
    patched: list[str] = field(default_factory=list)
    reloaded: list[str] = field(default_factory=list)
    edited: list[str] = field(default_factory=list)
    replaced: dict[str, list["weakref.ref[type]"]] = field(default_factory=dict)
    new_factory: Optional[Callable[[], object]] = None


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
    # Reject dependencies by their real install location *before* the
    # project-root check, so a project-local ``.venv/`` (site-packages under the
    # project root) is still excluded. Editable installs (``pip install
    # -e``) whose source lives in the tree resolve outside these directories, so
    # they stay reloadable — that source is genuinely the user's code.
    for site_dir in _site_directories():
        try:
            resolved.relative_to(site_dir)
        except ValueError:
            continue
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


def _read_source(filename: str) -> Optional[str]:
    """The file's text as the import system decodes it, or ``None`` when it cannot be read."""
    try:
        return importlib.util.decode_source(Path(filename).read_bytes())
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


class _WithoutBodies(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.body = []
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.body = []
        return node


def _outside_bodies(source: str) -> str:
    """Everything a re-execution would evaluate: the source with every def body taken out."""
    return ast.dump(_WithoutBodies().visit(ast.parse(source)))


def _imports(name: str, filename: str, source: str, user_names: set[str]) -> set[str]:
    """The user modules ``name`` imports, read from its import statements at any depth."""
    package = name if Path(filename).name == "__init__.py" else name.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                try:
                    base = importlib.util.resolve_name("." * node.level + base, package)
                except ImportError:
                    continue
            found.add(base)
            found.update(f"{base}.{alias.name}" for alias in node.names)
    return {dep for dep in found if dep in user_names and dep != name}


class Reloader:
    """Applies saves to the user modules under one project root.

    It keeps the source each module last ran with, which is what a save is
    compared against.
    """

    def __init__(self, project_root: Path) -> None:
        """Start with no source on record.

        Args:
            project_root: The directory the user's modules live under.
        """
        self._project_root = project_root.resolve()
        # A module with no entry, or with None, has no source the edit can be compared against.
        self._ran: dict[str, Optional[str]] = {}
        # The watcher's thread tracks while the UI thread reloads.
        self._lock = threading.Lock()
        self.last: ReloadResult = ReloadResult()
        """The result of the latest :meth:`reload`, filled as far as it got when it raised."""

    def track(self) -> list[Path]:
        """Put each loaded user module not yet on record on record, with its file as the source it ran with.

        Called at startup and on every poll, so a module imported later is on
        record before its first save.

        Returns:
            The files of the loaded user modules.
        """
        files = self._files()
        with self._lock:
            for name, filename in files.items():
                if name not in self._ran:
                    self._ran[name] = _read_source(filename)
        return [Path(filename) for filename in files.values()]

    def reload(self, old_factory: Optional[Callable[[], object]] = None) -> ReloadResult:
        """Apply every saved file and re-fetch the root factory.

        Args:
            old_factory: The current root factory.

        Returns:
            What was patched and what was re-executed.

        Raises:
            SyntaxError: A saved file does not compile. Nothing was applied.
            Exception: Whatever a re-executed module raised. The modules
                re-executed before it stay applied.
        """
        with self._lock:
            return self._apply(old_factory)

    def _apply(self, old_factory: Optional[Callable[[], object]]) -> ReloadResult:
        self.last = result = ReloadResult()
        files = self._files()
        sources: dict[str, str] = {}
        for name, filename in files.items():
            source = _read_source(filename)
            if source is None:
                continue
            if name not in self._ran and runs_source(sys.modules[name], source):
                self._ran[name] = source
            if source != self._ran.get(name):
                sources[name] = source
        result.changed = sorted(sources)
        for name, source in sources.items():
            compile(source, files[name], "exec", dont_inherit=True)

        edited = {name for name, source in sources.items() if not self._only_bodies_differ(name, source)}
        for name in sorted(set(sources) - set(self._with_importers(edited, files))):
            try:
                patch_bodies(sys.modules[name], self._ran[name] or "", sources[name])
            except (Unpatchable, ValueError) as exc:
                logger.debug("hot reload: %s is re-executed: %s", name, exc)
                edited.add(name)
            else:
                self._ran[name] = sources[name]
                result.patched.append(name)

        result.edited = sorted(edited)
        stale = self._with_importers(edited, files)
        # A module patched before a later one was refused may import the refused one.
        result.patched = [name for name in result.patched if name not in stale]
        self._reexecute(stale, files, result)
        if old_factory is not None:
            result.new_factory = _refetch_factory(old_factory)
        logger.debug("hot reload: patched %s, re-executed %s", result.patched, result.reloaded)
        return result

    def _files(self) -> dict[str, str]:
        """The loaded user modules and their files."""
        return {
            name: str(module.__file__)
            for name, module in identify_user_modules(self._project_root).items()
            if name != "__main__"
        }

    def _only_bodies_differ(self, name: str, source: str) -> bool:
        ran = self._ran.get(name)
        return ran is not None and _outside_bodies(ran) == _outside_bodies(source)

    def _with_importers(self, names: set[str], files: dict[str, str]) -> list[str]:
        """``names`` and every user module that imports one of them, each after the ones it imports."""
        if not names:
            return []
        user_names = set(files)
        imports: dict[str, set[str]] = {}
        for name, filename in files.items():
            source = _read_source(filename)
            imports[name] = _imports(name, filename, source, user_names) if source is not None else set()

        stale = set(names)
        grew = True
        while grew:
            grew = False
            for name, deps in imports.items():
                if name not in stale and deps & stale:
                    stale.add(name)
                    grew = True

        ordered: list[str] = []

        def visit(name: str, visiting: frozenset[str]) -> None:
            if name in ordered or name in visiting:
                return
            for dep in sorted(imports[name] & stale):
                visit(dep, visiting | {name})
            ordered.append(name)

        for name in sorted(stale):
            visit(name, frozenset())
        return ordered

    def _reexecute(self, names: list[str], files: dict[str, str], result: ReloadResult) -> None:
        if not names:
            return
        # A module that is not reached, or raises, no longer matches any source on record.
        for name in names:
            self._ran[name] = None
        importlib.invalidate_caches()
        for name in names:
            module = sys.modules[name]
            # The cached bytecode is dated to the second: a save within the same second would be missed.
            try:
                os.remove(importlib.util.cache_from_source(files[name]))
            except (OSError, ValueError, NotImplementedError):
                pass
            source = _read_source(files[name])
            result.replaced[name] = [
                weakref.ref(value)
                for value in vars(module).values()
                if isinstance(value, type) and value.__module__ == name
            ]
            importlib.reload(module)
            result.reloaded.append(name)
            self._ran[name] = source
