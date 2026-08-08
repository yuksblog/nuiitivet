"""OverlayRoute for modal overlay layers."""

from __future__ import annotations

from typing import Callable

from nuiitivet.navigation.transition_spec import TransitionSpec, Transitions
from nuiitivet.navigation.route import Route
from nuiitivet.widgeting.widget import Widget


class OverlayRoute(Route):
    """A modal route shown on the Overlay layer."""

    def __init__(
        self,
        builder: Callable[[], Widget],
        transition_spec: TransitionSpec | None = None,
    ) -> None:
        """Initialize an overlay route.

        The route describes *content* only. Barrier / backdrop and dismissal are
        presentation concerns owned by the :meth:`Overlay.show` call that
        presents this route, so the same route can be shown with or without a
        backdrop.
        """
        super().__init__(
            builder=builder,
            transition_spec=transition_spec or Transitions.empty(),
        )
