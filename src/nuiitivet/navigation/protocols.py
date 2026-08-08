"""Typed navigation surface for ViewModels."""

from __future__ import annotations

from typing import Any, Protocol

from nuiitivet.navigation.route import Route
from nuiitivet.widgeting.widget import Widget


class NavigatorProtocol(Protocol):
    """The navigation surface a ViewModel depends on.

    Annotate an injected navigator with this protocol so the ViewModel stays
    independent of the widget tree::

        class CartViewModel:
            def __init__(self, navigator: NavigatorProtocol) -> None:
                self._navigator = navigator

            def checkout(self) -> None:
                self._navigator.push(OrderCompleteIntent())

    :class:`~nuiitivet.navigation.navigator.Navigator` and
    :class:`~nuiitivet.material.navigator.MaterialNavigator` satisfy it
    structurally, and a hand-written fake needs only these three methods --
    no widget tree and no ``App``.
    """

    def push(self, route_or_widget_or_intent: Route | Widget | Any) -> None:
        """Push a route, a widget, or an intent onto the navigation stack."""
        ...

    def pop(self) -> None:
        """Pop the topmost route."""
        ...

    def can_pop(self) -> bool:
        """Return whether a route below the topmost one exists."""
        ...
