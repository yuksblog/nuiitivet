"""Design-agnostic contracts for overlay layer composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from nuiitivet.widgeting.widget import Widget

from .transition_state import OverlayTransitionState


@dataclass(frozen=True, slots=True)
class OverlayLayerCompositionContext:
    """Input context for composing a rendered overlay layer.

    Attributes:
        content: Route content widget for the current overlay entry.
        transition_state: Transition lifecycle observables and transition spec token for this entry.
        passthrough: Whether the overlay should pass input through to background.
        barrier_color: RGBA barrier color.
        barrier_dismissible: Whether tapping barrier dismisses the entry.
        on_barrier_click: Callback invoked when barrier is tapped.
        position_content: Function to place content according to overlay position.
    """

    content: Widget
    transition_state: OverlayTransitionState
    passthrough: bool
    barrier_color: tuple[int, int, int, int]
    barrier_dismissible: bool
    on_barrier_click: Callable[[], None]
    position_content: Callable[[Widget], Widget]


class OverlayLayerComposer(Protocol):
    """Composable boundary for visual overlay layer rendering."""

    def compose(self, context: OverlayLayerCompositionContext) -> Widget:
        """Compose a widget layer from overlay transition facts."""


__all__ = ["OverlayLayerComposer", "OverlayLayerCompositionContext"]
