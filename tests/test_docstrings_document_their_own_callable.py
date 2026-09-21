"""A callable documents its own arguments; the class docstring routes.

A parameter list in a class docstring is a second copy of the one in
``__init__``, and the two drift apart. The class docstring names the other ways
of constructing the class instead, so reading the class leads to them.
"""

from __future__ import annotations

import inspect
import re

import nuiitivet.material as nv

# A parameter-section heading, Google style or not, with or without its colon.
PARAMETER_SECTION = re.compile(r"^\s*(Args|Arguments|Parameters|Params|Keyword Args)\s*:?\s*$", re.MULTILINE)

# Resolution hooks a widget calls on its own style class, not ways an app
# constructs one.
NOT_A_CONSTRUCTOR = {"from_theme", "preset"}


def _public_classes() -> list[tuple[str, type]]:
    found = [
        (name, obj)
        for name in nv.__all__
        if inspect.isclass(obj := getattr(nv, name)) and obj.__module__.startswith("nuiitivet.")
    ]
    assert found, "no public classes found on nuiitivet.material"
    return found


def _alternative_constructors(name: str, cls: type) -> list[str]:
    found: list[str] = []
    for attr, value in vars(cls).items():
        if attr.startswith("_") or attr in NOT_A_CONSTRUCTOR or not isinstance(value, (classmethod, staticmethod)):
            continue
        returns = str(value.__func__.__annotations__.get("return", "")).strip("'\"")
        if returns in (name, "Self") or returns.endswith(f".{name}"):
            found.append(attr)
    return found


def test_class_docstrings_hold_no_parameter_list() -> None:
    violations = [
        f"{cls.__module__}.{name}"
        for name, cls in _public_classes()
        if PARAMETER_SECTION.search(vars(cls).get("__doc__") or "")
    ]
    assert not violations, (
        "A class docstring holds no parameter list -- move it to __init__'s Args:, "
        "or to Attributes: for a dataclass:\n" + "\n".join(violations)
    )


def test_class_docstrings_name_their_alternative_constructors() -> None:
    violations = [
        f"{cls.__module__}.{name}: {constructor}"
        for name, cls in _public_classes()
        for constructor in _alternative_constructors(name, cls)
        if not re.search(rf"\b{constructor}\b", vars(cls).get("__doc__") or "")
    ]
    assert not violations, "A class docstring names every other way of constructing the class:\n" + "\n".join(
        violations
    )
