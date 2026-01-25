from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .widget import Widget


class ModifierElement:
    """Individual modifier element that can wrap or modify a widget."""

    def apply(self, widget: "Widget") -> "Widget":
        """Apply this modifier to a widget, potentially returning a new wrapper widget."""
        raise NotImplementedError

    def __or__(self, other: "ModifierElement") -> "Modifier":
        """Support | operator to combine two modifier elements into a Modifier chain."""
        modifier = Modifier()
        modifier = modifier.then(self)
        return modifier.then(other)


class Modifier(ModifierElement):
    """Base modifier class that can be chained."""

    def __init__(self) -> None:
        self._modifiers: list[ModifierElement] = []

    def then(self, element: ModifierElement) -> "Modifier":
        """Chain another modifier element."""
        new_modifier = Modifier()
        new_modifier._modifiers = self._modifiers + [element]
        return new_modifier

    def __or__(self, element: ModifierElement) -> "Modifier":
        """Support | operator for chaining."""
        return self.then(element)

    def apply(self, widget: "Widget") -> "Widget":
        """Apply all modifier elements to a widget."""
        result = widget
        for element in self._modifiers:
            result = element.apply(result)
        return result
