"""The presets layout edit mode picks from, per widget class.

A preset is one classmethod of a style class (``ButtonStyle.filled``) or one
role of the type scale (``TypeScale.TITLE_MEDIUM``). The table here is what
the pick list shows, and what the check after the reload rebuilds to compare
the widget against.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from nuiitivet.material.styles.button_style import ButtonStyle, IconButtonStyle, IconToggleButtonStyle
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.theme.type_scale import TypeScale


@dataclass(frozen=True)
class Family:
    """The presets one widget class picks from.

    Attributes:
        keyword: The keyword the preset is passed as.
        companion: The class the presets hang off, by name, spelled beside the widget's own.
        names: The preset names, in the order the list shows them.
        sizes: The size tokens the presets take; empty when they take none.
        default: The name and size in effect when the keyword is absent.
        called: Whether a preset is a call; a type-scale role is an attribute.
    """

    keyword: str
    companion: str
    names: tuple[str, ...]
    sizes: tuple[str, ...]
    default: tuple[str, Optional[str]]
    called: bool = True


_SIZES = ("xs", "s", "m", "l", "xl")
_ROLES = tuple(name for name in vars(TypeScale) if name.isupper())

#: The families by widget class name; a subclass picks from its base's.
FAMILIES: dict[str, Family] = {
    "Button": Family(
        "style", "ButtonStyle", ("filled", "tonal", "outlined", "elevated", "text"), _SIZES, ("filled", "s")
    ),
    "IconButton": Family(
        "style",
        "IconButtonStyle",
        ("standard", "filled", "tonal", "outlined", "vibrant", "filled_vibrant", "tonal_vibrant", "outlined_vibrant"),
        _SIZES,
        ("standard", "s"),
    ),
    "IconToggleButton": Family(
        "style", "IconToggleButtonStyle", ("standard", "filled", "tonal", "outlined"), _SIZES, ("standard", "s")
    ),
    "Card": Family("style", "CardStyle", ("filled", "elevated", "outlined"), (), ("filled", None)),
    "TextBase": Family("type_scale", "TypeScale", _ROLES, (), ("BODY_MEDIUM", None), called=False),
}

_CLASSES: dict[str, Any] = {
    "ButtonStyle": ButtonStyle,
    "IconButtonStyle": IconButtonStyle,
    "IconToggleButtonStyle": IconToggleButtonStyle,
    "CardStyle": CardStyle,
    "TypeScale": TypeScale,
}


def family_of(node: Any) -> Optional[Family]:
    """The presets ``node``'s class picks from, found by its name or a base class's, or ``None``."""
    for cls in type(node).__mro__:
        family = FAMILIES.get(cls.__name__)
        if family is not None:
            return family
    return None


def value_of(family: Family, name: str, size: Optional[str]) -> Any:
    """The object the preset ``name`` at ``size`` resolves to, as the widget holds it."""
    member = getattr(_CLASSES[family.companion], name)
    if not family.called:
        return member
    return member(size) if size is not None else member()


__all__ = ["FAMILIES", "Family", "family_of", "value_of"]
