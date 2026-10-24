"""What layout edit mode can pick for a widget, read from the widget's own declaration.

A widget names the constructor keywords it takes a preset for, and the class
each preset hangs off, in ``Widget.editable_parameters()``. This module reads the choices
from that class: its preset classmethods with the parameters each takes
(``ButtonStyle.filled(size="m")``), or its uppercase attributes
(``TypeScale.TITLE_LARGE``), and which choice is in effect when the keyword
is absent. Nothing here names a widget or a design system.
"""

from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Iterable, Mapping, Optional


@dataclass(frozen=True)
class Parameter:
    """One parameter a preset takes: ``size``, one of ``xs`` to ``xl``, ``s`` when omitted.

    Attributes:
        name: The parameter's name.
        choices: The values its ``Literal`` admits, in order.
        default: The value in effect when the argument is omitted.
    """

    name: str
    choices: tuple[Any, ...]
    default: Any

    def parse(self, token: str) -> Any:
        """The choice spelled ``token``, or ``token`` itself when none is."""
        return next((choice for choice in self.choices if str(choice) == token), token)


@dataclass(frozen=True)
class Choice:
    """One preset: its name, and the parameters it takes."""

    name: str
    parameters: tuple[Parameter, ...] = ()


@dataclass(frozen=True)
class Family:
    """The choices one keyword offers.

    Attributes:
        keyword: The constructor keyword a pick is written to.
        companion: The class the choices hang off.
        choices: The presets, in the order the list shows them.
        called: Whether a choice is a call; an attribute is not.
        default: The choice in effect when the keyword is absent, by name, or ``None`` when no choice is.
    """

    keyword: str
    companion: type
    choices: tuple[Choice, ...]
    called: bool
    default: Optional[str]

    @property
    def names(self) -> tuple[str, ...]:
        """The choices' names, in order."""
        return tuple(choice.name for choice in self.choices)

    def choice(self, name: Optional[str]) -> Optional[Choice]:
        """The choice named ``name``, or ``None``."""
        return next((choice for choice in self.choices if choice.name == name), None)


def families_of(node: Any) -> tuple[Family, ...]:
    """What ``node`` declares editable, one family per keyword, in the declared order.

    A keyword whose class offers no choice is left out.
    """
    declared = getattr(type(node), "editable_parameters", None)
    if not callable(declared):
        return ()
    families = (_family(node, keyword, companion) for keyword, companion in declared().items())
    return tuple(family for family in families if family.choices)


def family_of(node: Any, keyword: str) -> Optional[Family]:
    """The family ``node`` declares for ``keyword``, or ``None``."""
    return next((family for family in families_of(node) if family.keyword == keyword), None)


def value_of(family: Family, name: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
    """The object the choice ``name`` builds with ``arguments``, as the widget holds it."""
    member = getattr(family.companion, name)
    return member(**(arguments or {})) if family.called else member


def held(node: Any, keyword: str) -> list[Any]:
    """The values ``node`` may hold for ``keyword``: the property of that name, and every attribute."""
    values = [getattr(node, keyword, None)]
    try:
        values.extend(vars(node).values())
    except TypeError:
        pass
    return values


def same(value: Any, other: Any) -> bool:
    """Equality that a value with an odd ``__eq__`` cannot break."""
    try:
        return bool(value == other)
    except Exception:
        return False


@lru_cache(maxsize=None)
def choices_of(companion: type) -> tuple[tuple[Choice, ...], bool]:
    """The presets ``companion`` offers, and whether they are calls.

    A preset is a public classmethod whose every parameter has a default and
    a ``Literal`` annotation. ``default`` is not one: it names the default.
    A class with no classmethod offers its uppercase attributes.
    """
    methods = [name for name, member in vars(companion).items() if _is_public_classmethod(name, member)]
    if methods:
        found = (_choice(companion, name) for name in methods if name != "default")
        return tuple(choice for choice in found if choice is not None), True
    return tuple(Choice(name) for name in vars(companion) if name.isupper()), False


def _is_public_classmethod(name: str, member: Any) -> bool:
    return isinstance(member, classmethod) and not name.startswith("_")


def _all_optional(method: Any) -> bool:
    """Whether ``method`` can be called with no argument."""
    try:
        parameters = inspect.signature(method).parameters.values()
    except (TypeError, ValueError):
        return False
    return all(parameter.default is not inspect.Parameter.empty for parameter in parameters)


def _choice(companion: type, name: str) -> Optional[Choice]:
    method = getattr(companion, name)
    try:
        hints = typing.get_type_hints(method)
    except Exception:
        # An annotation only the type checker can see (``theme: "Theme"``)
        # is not a ``Literal``.
        hints = {}
    parameters: list[Parameter] = []
    for parameter in inspect.signature(method).parameters.values():
        hint = hints.get(parameter.name)
        if parameter.default is inspect.Parameter.empty or typing.get_origin(hint) is not typing.Literal:
            return None
        parameters.append(Parameter(parameter.name, typing.get_args(hint), parameter.default))
    return Choice(name, tuple(parameters))


def _family(node: Any, keyword: str, companion: type) -> Family:
    choices, called = choices_of(companion)
    family = Family(keyword, companion, choices, called, None)
    return replace(family, default=_default(node, family))


def _default(node: Any, family: Family) -> Optional[str]:
    """The choice equal to the companion's ``default()``, else to what the live widget holds, else ``None``."""
    named = getattr(family.companion, "default", None)
    if family.called and callable(named) and _all_optional(named):
        candidates: Iterable[Any] = (named(),)
    else:
        candidates = held(node, family.keyword)
    for choice in family.choices:
        value = value_of(family, choice.name)
        if any(same(candidate, value) for candidate in candidates):
            return choice.name
    return None


__all__ = [
    "Choice",
    "Family",
    "Parameter",
    "choices_of",
    "families_of",
    "family_of",
    "held",
    "same",
    "value_of",
]
