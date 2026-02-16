"""Material-specific navigator defaults."""

from __future__ import annotations

from nuiitivet.navigation.navigator import Navigator
from nuiitivet.navigation.route import PageRoute, Route
from nuiitivet.widgeting.widget import Widget

from .transition_spec import MaterialTransitions


class MaterialNavigator(Navigator):
    """Navigator that applies Material default transition specs."""

    def _route_from_widget(self, widget: Widget) -> Route:
        return PageRoute(
            builder=lambda: widget,
            transition_spec=MaterialTransitions.page(),
        )


__all__ = ["MaterialNavigator"]
