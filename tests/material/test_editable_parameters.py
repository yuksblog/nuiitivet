"""Every widget whose style class offers presets declares them for layout edit mode.

A widget that forgets ``editable_parameters()`` gets no bar in the mode and nothing
says so; this test does.
"""

from __future__ import annotations

import inspect
import sys
import typing

import nuiitivet.material as nv
from nuiitivet.dev.presets import choices_of
from nuiitivet.widgeting.widget import Widget


def _public_widgets() -> list[type[Widget]]:
    found = [
        obj
        for name in nv.__all__
        if inspect.isclass(obj := getattr(nv, name)) and issubclass(obj, Widget)
    ]
    assert found
    return found


def _classes_in(hint: object) -> list[type]:
    if inspect.isclass(hint):
        return [hint]
    return [arg for arg in typing.get_args(hint) if inspect.isclass(arg)]


def _preset_parameters(cls: type[Widget]) -> dict[str, type]:
    """The constructor parameters annotated with a style class that offers presets, with that class."""
    module = sys.modules[cls.__module__]
    constructor = vars(cls).get("__init__") or cls.__init__  # type: ignore[misc]
    try:
        hints = typing.get_type_hints(constructor, globalns={**vars(nv), **vars(module)})
    except Exception:
        return {}
    found: dict[str, type] = {}
    for name, hint in hints.items():
        for candidate in _classes_in(hint):
            if candidate.__name__.endswith("Style") and choices_of(candidate)[0]:
                found[name] = candidate
    return found


def test_every_widget_with_a_preset_style_declares_it() -> None:
    missing = [
        f"{cls.__name__}.{keyword}: {annotated.__name__}"
        for cls in _public_widgets()
        for keyword, annotated in _preset_parameters(cls).items()
        if keyword not in cls.editable_parameters()
    ]
    assert not missing, (
        "A widget declares every keyword it takes a preset for in editable_parameters():\n"
        + "\n".join(missing)
    )


def test_every_declared_companion_with_preset_calls_names_its_default() -> None:
    """``default()`` is the preset a widget renders with before it is mounted; the bar shows it as the default."""
    for cls in _public_widgets():
        for keyword, companion in cls.editable_parameters().items():
            _choices, called = choices_of(companion)
            if called:
                assert callable(getattr(companion, "default", None)), f"{companion.__name__} has no default()"


def test_every_declared_companion_offers_choices_of_the_parameters_type() -> None:
    for cls in _public_widgets():
        annotated = _preset_parameters(cls)
        for keyword, companion in cls.editable_parameters().items():
            choices, called = choices_of(companion)
            assert choices, f"{cls.__name__}.{keyword}: {companion.__name__} offers no preset"
            member = getattr(companion, choices[0].name)
            value = member() if called else member
            if keyword in annotated:
                assert isinstance(value, annotated[keyword]), f"{cls.__name__}.{keyword} takes {annotated[keyword]}"
