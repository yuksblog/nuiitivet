"""DialogRoute for modal overlay dialogs."""

from __future__ import annotations

from typing import Callable

from nuiitivet.navigation.transition_spec import TransitionSpec, Transitions
from nuiitivet.navigation.route import Route
from nuiitivet.widgeting.widget import Widget


class DialogRoute(Route):
    """A modal route shown on the Overlay layer."""

    def __init__(
        self,
        builder: Callable[[], Widget],
        transition_spec: TransitionSpec | None = None,
        *,
        barrier_color: tuple[int, int, int, int] = (0, 0, 0, 128),
        barrier_dismissible: bool = True,
    ) -> None:
        super().__init__(
            builder=builder,
            transition_spec=transition_spec or Transitions.empty(),
        )
        self.barrier_color = barrier_color
        self.barrier_dismissible = bool(barrier_dismissible)
