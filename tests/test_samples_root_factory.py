"""Every sample must pass a factory, not a widget instance, as Window content.

Hot reload rebuilds the tree by re-invoking the window's root factory, so a
sample that passes a built widget (``content=Foo()`` or a variable holding
one) silently loses hot reload for anyone following the README's dev-runner
instructions. Render-to-PNG branches are exempt: they never hot reload.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SAMPLES = Path(__file__).parent.parent / "samples"


def _window_content_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    factory_names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._parent = parent  # type: ignore[attr-defined]

    def in_png_branch(node: ast.AST) -> bool:
        current: ast.AST | None = node
        while current is not None:
            if isinstance(current, ast.If) and any(
                isinstance(n, ast.Name) and n.id.startswith("png")
                for n in ast.walk(current.test)
            ):
                return True
            current = getattr(current, "_parent", None)
        return False

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = getattr(node.func, "attr", getattr(node.func, "id", ""))
        if func_name != "Window":
            continue
        for kw in node.keywords:
            if kw.arg != "content":
                continue
            value = kw.value
            is_factory = isinstance(value, ast.Lambda) or (
                isinstance(value, ast.Name) and value.id in factory_names
            )
            if not is_factory and not in_png_branch(node):
                violations.append(
                    f"{path.relative_to(SAMPLES)}:{node.lineno}: "
                    f"content={ast.unparse(value)}"
                )
    return violations


@pytest.mark.parametrize(
    "path",
    sorted(SAMPLES.rglob("*.py")),
    ids=lambda p: str(p.relative_to(SAMPLES)),
)
def test_sample_passes_root_factory(path: Path) -> None:
    violations = _window_content_violations(path)
    assert not violations, (
        "Window(content=...) must receive a factory (a widget subclass, a "
        "module-level function, or a lambda), not a widget instance -- an "
        "instance root disables hot reload:\n" + "\n".join(violations)
    )
