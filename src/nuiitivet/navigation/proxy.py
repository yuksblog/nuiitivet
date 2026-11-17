"""What ``Navigator.proxy(widget)`` returns."""

from __future__ import annotations

from typing import Any

from nuiitivet.transition.spec import TransitionSpec
from nuiitivet.widgeting.context_lookup import ContextProxy
from nuiitivet.widgeting.widget import Widget

from .protocols import NavigatorProtocol


class NavigatorProxy(ContextProxy[NavigatorProtocol]):
    """Forwards :class:`~nuiitivet.navigation.protocols.NavigatorProtocol` to the navigator of one widget.

    A call after the widget is unmounted does nothing.
    """

    def push(self, screen: Widget | Any, *, transition: TransitionSpec | None = None) -> None:
        """Push a widget, or an intent, onto the navigation stack.

        Args:
            screen: A widget, or an intent resolved through the navigator's routes.
            transition: The transition the widget moves with; widgets only.
        """
        navigator = self._provider()
        if navigator is not None:
            navigator.push(screen, transition=transition)

    def pop(self) -> None:
        """Pop the topmost screen."""
        navigator = self._provider()
        if navigator is not None:
            navigator.pop()

    def can_pop(self) -> bool:
        """Return whether a screen below the topmost one exists."""
        navigator = self._provider()
        return navigator is not None and navigator.can_pop()
