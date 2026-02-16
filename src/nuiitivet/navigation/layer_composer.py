"""Design-agnostic contracts for navigation layer composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from nuiitivet.widgeting.widget import Widget

from .transition_spec import TransitionPhase, TransitionSpec


NavigationTransitionKind = Literal["push", "pop"]


@dataclass(frozen=True, slots=True)
class NavigationLayerCompositionContext:
    """Input context for composing one navigation transition frame.

    Attributes:
        canvas: Paint target object.
        x: Paint origin x.
        y: Paint origin y.
        width: Paint width.
        height: Paint height.
        kind: Transition kind (push/pop).
        from_widget: Source widget of the transition.
        to_widget: Destination widget of the transition.
        from_phase: Lifecycle phase for ``from_widget``.
        to_phase: Lifecycle phase for ``to_widget``.
        progress: Normalized transition progress in ``[0.0, 1.0]``.
        from_transition_spec: Transition spec for ``from_widget``.
        to_transition_spec: Transition spec for ``to_widget``.
    """

    canvas: Any
    x: int
    y: int
    width: int
    height: int
    kind: NavigationTransitionKind
    from_widget: Widget
    to_widget: Widget
    from_phase: TransitionPhase
    to_phase: TransitionPhase
    progress: float
    from_transition_spec: TransitionSpec
    to_transition_spec: TransitionSpec


class NavigationLayerComposer(Protocol):
    """Visual composition boundary for navigation painting."""

    def paint_static(self, *, canvas: Any, widget: Widget, x: int, y: int, width: int, height: int) -> None:
        """Paint a non-transitioning route widget."""

    def paint_transition(self, context: NavigationLayerCompositionContext) -> None:
        """Paint a transition frame between two route widgets."""


__all__ = [
    "NavigationLayerComposer",
    "NavigationLayerCompositionContext",
    "NavigationTransitionKind",
]
