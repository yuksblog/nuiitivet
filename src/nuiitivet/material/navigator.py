"""Material-specific navigator defaults."""

from __future__ import annotations

from nuiitivet.navigation.layer_composer import NavigationLayerComposer
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.navigation.route import Route
from nuiitivet.widgeting.widget import Widget

from .navigation_visual_state import MaterialNavigationLayerComposer
from .transition_spec import MaterialTransitions


class MaterialNavigator(Navigator):
    """Navigator that applies Material default transition specs.

    Defaults its layer composer to :class:`MaterialNavigationLayerComposer` so
    that page transitions actually render their Material fade — including when
    the navigator is built directly via :meth:`Navigator.intents` /
    :meth:`Navigator.routes` (not only the implicit navigator ``MaterialApp``
    wires up). Without it the core :class:`_DefaultNavigationLayerComposer`
    composites both routes at full opacity, so the transition never animates.
    """

    def __init__(
        self,
        screen: Route | Widget | None = None,
        *,
        layer_composer: NavigationLayerComposer | None = None,
    ) -> None:
        super().__init__(
            screen,
            layer_composer=layer_composer or MaterialNavigationLayerComposer(),
        )

    def _route_from_widget(self, widget: Widget) -> Route:
        return Route(
            builder=lambda: widget,
            transition_spec=MaterialTransitions.page(),
        )


__all__ = ["MaterialNavigator"]
