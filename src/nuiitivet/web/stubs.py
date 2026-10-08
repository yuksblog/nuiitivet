"""The stubs of the server-only modules, and the modules that hold a marked function, read from the sources.

Nothing here imports the app: a build must not run server code, and the
server-only modules are the ones that would open a database on import.
"""

from __future__ import annotations

import ast
import builtins
import copy
from pathlib import Path
from typing import Iterator

_SERVER_ONLY = "server_only"
# Directories whose files are never part of the app.
SKIPPED_DIRS = {"__pycache__", "node_modules", "venv"}
_SERVER = "server"
_WORKER = "worker"


def _calls(statement: ast.stmt, name: str) -> bool:
    """Whether *statement* is a call of ``name(...)`` or ``<anything>.name(...)``."""
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return False
    target = statement.value.func
    return (isinstance(target, ast.Name) and target.id == name) or (
        isinstance(target, ast.Attribute) and target.attr == name
    )


def _decorated_with(function: ast.FunctionDef, name: str) -> bool:
    for decorator in function.decorator_list:
        if (isinstance(decorator, ast.Name) and decorator.id == name) or (
            isinstance(decorator, ast.Attribute) and decorator.attr == name
        ):
            return True
    return False


def _module_name(path: Path, root: Path) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _app_files(root: Path) -> Iterator[Path]:
    """The ``.py`` files of the app's directory, sorted, without the directories that are never part of the app."""
    for path in sorted(root.rglob("*.py")):
        if not any(part.startswith(".") or part in SKIPPED_DIRS for part in path.relative_to(root).parts):
            yield path


def _holds(path: Path, decorator: str) -> bool:
    """Whether a top-level function of the file at *path* is decorated with *decorator*."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return any(isinstance(node, ast.FunctionDef) and _decorated_with(node, decorator) for node in tree.body)


class ServerOnly:
    """The server-only files of an app directory, and the stubs that replace them."""

    def __init__(self, root: Path) -> None:
        """Initialize ServerOnly.

        Args:
            root: The app's directory.
        """
        self.root = root
        self._scopes: list[Path] = []
        for path in _app_files(root):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if any(_calls(statement, _SERVER_ONLY) for statement in tree.body):
                self._scopes.append(path.parent if path.name == "__init__.py" else path)

    def covers(self, path: Path) -> bool:
        """Whether *path*, a file of the app directory, stays on the server.

        Args:
            path: An absolute path under the app's directory.
        """
        return any(path == scope or scope in path.parents for scope in self._scopes)

    def stubs(self) -> Iterator[tuple[str, str]]:
        """Each stub module as ``(path relative to the app directory, source)``.

        A package's ``__init__.py`` always gets one, so the stubs under it
        import. Any other module gets one only if it holds a server function.
        """
        for path in _app_files(self.root):
            if not self.covers(path):
                continue
            source = stub_source(path, _module_name(path, self.root))
            if source is not None or path.name == "__init__.py":
                yield path.relative_to(self.root).as_posix(), source or ""


def stub_source(path: Path, module: str) -> str | None:
    """The page's module for a server-only one: each ``@server`` signature, with the call sent to the server.

    Args:
        path: The server-only module's file.
        module: Its dotted name.

    Returns:
        The source, or ``None`` when the module holds no server function.

    Raises:
        RuntimeError: If a signature uses a name the module does not import.
            The page cannot get a type defined in a server-only module.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and _decorated_with(node, _SERVER)
    ]
    if not functions:
        return None

    needed: dict[str, str] = {}
    for function in functions:
        for name in _names_in_signature(function):
            needed.setdefault(name, function.name)

    lines = ["from nuiitivet.remote.function import stub as _stub"]
    bound: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == "__future__":
            lines.insert(0, ast.unparse(statement))
        elif isinstance(statement, (ast.Import, ast.ImportFrom)):
            names = {(alias.asname or alias.name).split(".")[0] for alias in statement.names}
            if names & needed.keys():
                bound |= names
                lines.append(ast.unparse(statement))

    for name, function_name in needed.items():
        if name not in bound and not hasattr(builtins, name):
            raise RuntimeError(
                f"{module}.{function_name}: {name} is not imported into {path.name}, so the page cannot "
                "get it; a type in a server function's signature comes from a module the page gets"
            )
    for function in functions:
        stub = copy.copy(function)
        stub.body = [ast.Expr(ast.Constant(...))]
        stub.decorator_list = [ast.Name("_stub", ast.Load())]
        lines.extend(["", "", ast.unparse(ast.fix_missing_locations(stub))])
    return "\n".join(lines) + "\n"


def server_modules(root: Path) -> list[str]:
    """The dotted names of the app's modules that hold a ``@server`` function, for the server to import.

    Args:
        root: The app's directory.
    """
    return [_module_name(path, root) for path in _app_files(root) if _holds(path, _SERVER)]


def worker_modules(root: Path) -> list[str]:
    """The dotted names of the app's modules that hold a ``@worker`` function, for the page's worker to import.

    A server-only module is left out: the desktop refuses a worker function there.

    Args:
        root: The app's directory.
    """
    server_only = ServerOnly(root)
    return [
        _module_name(path, root)
        for path in _app_files(root)
        if not server_only.covers(path) and _holds(path, _WORKER)
    ]


def _names_in_signature(function: ast.FunctionDef) -> Iterator[str]:
    nodes: list[ast.AST] = [function.args]
    if function.returns is not None:
        nodes.append(function.returns)
    for root in nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.Name):
                yield node.id


__all__ = ["SKIPPED_DIRS", "ServerOnly", "server_modules", "stub_source", "worker_modules"]
