from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from nuiitivet.navigation.transition_spec import TransitionSpec, Transitions
from nuiitivet.widgeting.widget import Widget


@dataclass(slots=True)
class Route:
    """A unit of navigation.

    Notes:
        This is intentionally minimal for Phase 3.
    """

    builder: Callable[[], Widget]
    transition_spec: TransitionSpec = field(default_factory=lambda: Transitions.empty())

    _widget: Widget | None = None

    def build_widget(self) -> Widget:
        if self._widget is not None and getattr(self._widget, "_unmounted", False):
            self._widget = None
        if self._widget is None:
            self._widget = self.builder()
        return self._widget

    def dispose(self) -> None:
        if self._widget is None:
            return

        self._widget.unmount()
        self._widget = None


class PageRoute(Route):
    """Route for a page widget."""

    def __init__(self, builder: Callable[[], Widget], transition_spec: TransitionSpec | None = None) -> None:
        super().__init__(builder=builder, transition_spec=transition_spec or Transitions.empty())
