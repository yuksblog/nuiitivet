"""Keep every sample launchable by the dev runner (issue #658).

``python -m nuiitivet.dev run <file>`` imports the sample, calls its entry once
with no arguments, and expects that call to have built an ``App`` and called
``App.run()`` -- that is what hands the app off to hot reload and the dev bridge.
A sample that instead builds the app under ``if __name__ == "__main__":``, or
that hands an unstarted ``App`` back to its caller, cannot be run, hot-reloaded,
or driven at all.

``samples/`` is the corpus a user copies from, so the check is on the samples
rather than on the runner: one blessed shape, enforced statically. Nothing here
imports a sample or opens a window -- the AST says everything the contract needs.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SAMPLES = _ROOT / "samples"

_ENTRY = "main"


def _sample_files() -> list[pathlib.Path]:
    """Every runnable sample: package markers are not programs."""
    return sorted(p for p in _SAMPLES.rglob("*.py") if p.name != "__init__.py")


def _entry_of(tree: ast.Module) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """The module-level entry function, if the sample defines one."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == _ENTRY:
            return node
    return None


def _own_nodes(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    """Nodes belonging to ``fn`` itself, not to helpers nested inside it.

    Samples routinely define small builder helpers inside ``main()``; their
    returns and calls say nothing about how ``main()`` itself behaves.
    """
    owned: list[ast.AST] = []
    stack: list[ast.AST] = list(ast.iter_child_nodes(fn))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        owned.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return owned


def _ids(paths: list[pathlib.Path]) -> list[str]:
    return [str(p.relative_to(_SAMPLES)) for p in paths]


_FILES = _sample_files()


def test_samples_corpus_is_not_empty() -> None:
    """Guards the sweeps below against silently walking nothing."""
    assert _FILES, f"no samples found under {_SAMPLES}"


@pytest.mark.parametrize("path", _FILES, ids=_ids(_FILES))
def test_sample_defines_a_module_level_entry(path: pathlib.Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert _entry_of(tree) is not None, (
        f"{path.relative_to(_ROOT)} has no module-level '{_ENTRY}()'. "
        f"The dev runner calls '{_ENTRY}()' to build and run the app; building it "
        f'under \'if __name__ == "__main__":\' leaves nothing for it to call.'
    )


@pytest.mark.parametrize("path", _FILES, ids=_ids(_FILES))
def test_sample_entry_takes_no_required_arguments(path: pathlib.Path) -> None:
    """The runner calls the entry with no arguments, so every parameter is optional."""
    fn = _entry_of(ast.parse(path.read_text(encoding="utf-8")))
    assert fn is not None
    args = fn.args
    positional = args.posonlyargs + args.args
    required = [a.arg for a in positional[: len(positional) - len(args.defaults)]]
    required += [
        a.arg for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d is None
    ]
    assert required == [], (
        f"{path.relative_to(_ROOT)}: '{_ENTRY}()' requires {required}, but the dev "
        f"runner calls it with no arguments. Give every parameter a default "
        f'(the corpus convention is \'png_path: str = ""\').'
    )


@pytest.mark.parametrize("path", _FILES, ids=_ids(_FILES))
def test_sample_entry_runs_the_app(path: pathlib.Path) -> None:
    """The entry must start the app itself, not hand it back to its caller.

    ``App.run()`` is what the runner detects: under the dev session it registers
    the app and returns instead of blocking. An entry that ends in
    ``return app`` never reaches it, and ``main().run()`` in the ``__main__``
    guard runs only when the file is executed directly.
    """
    fn = _entry_of(ast.parse(path.read_text(encoding="utf-8")))
    assert fn is not None
    nodes = _own_nodes(fn)

    calls_run = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        for node in nodes
    )
    assert calls_run, (
        f"{path.relative_to(_ROOT)}: '{_ENTRY}()' never calls App.run(). "
        f"Build the app and run it inside '{_ENTRY}()' so the dev runner can "
        f"take it over."
    )

    returned = [
        ast.unparse(node)
        for node in nodes
        if isinstance(node, ast.Return) and node.value is not None
    ]
    assert returned == [], (
        f"{path.relative_to(_ROOT)}: '{_ENTRY}()' returns a value ({returned}); "
        f"an entry that hands an unstarted App back to its caller cannot be run "
        f"by the dev runner. Bare 'return' to bow out early is fine."
    )
