"""Intent resolution for overlay subclasses."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

from nuiitivet.widgeting.widget import Widget


# MEMO consider standardizing IntentResolver across Overlay and Navigator


class IntentResolver(Protocol):
    """Resolves an intent object to the widget the overlay presents."""

    def resolve(self, intent: Any) -> Widget: ...


def _type_qualname(tp: type[Any]) -> str:
    return f"{tp.__module__}.{tp.__qualname__}"


class MappingIntentResolver:
    """Resolves an intent through a table of intent types to widget factories.

    An intent whose type is missing from the table is matched by qualified name.
    A hot reload redefines the intent classes, so an intent created before the
    reload still finds its factory in the rebuilt table.
    """

    def __init__(self, factories: Mapping[type[Any], Callable[[Any], Widget]]) -> None:
        """Initialize the resolver.

        Args:
            factories: Mapping of intent types to functions that build the widget.
        """
        self._factories = dict(factories)

    def resolve(self, intent: Any) -> Widget:
        """Build the widget for ``intent``.

        Args:
            intent: The intent to resolve.

        Raises:
            RuntimeError: If no factory is registered for the intent's type.
        """
        factory = self._factories.get(type(intent))
        if factory is None:
            qualname = _type_qualname(type(intent))
            factory = next((f for tp, f in self._factories.items() if _type_qualname(tp) == qualname), None)
        if factory is None:
            raise RuntimeError(f"No overlay intent is registered: {type(intent).__name__}")
        return factory(intent)
