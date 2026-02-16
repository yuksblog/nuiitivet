"""Navigation primitives.

This package provides a minimal Navigator/Route API.
"""

from nuiitivet.navigation.navigator import Navigator
from nuiitivet.navigation.layer_composer import (
    NavigationLayerComposer,
    NavigationLayerCompositionContext,
    NavigationTransitionKind,
)
from nuiitivet.navigation.route import PageRoute, Route
from nuiitivet.navigation.stack_runtime import EntryLifecycle, RouteStackEntry, RouteStackRuntime
from nuiitivet.navigation.transition_state import TransitionLifecycle, TransitionState
from nuiitivet.navigation.transition_engine import TransitionEngine, TransitionMotionPreset, TransitionMotions
from nuiitivet.navigation.transition_spec import (
    EmptyTransitionSpec,
    TransitionPhase,
    TransitionSpec,
    Transitions,
)

__all__ = [
    "Navigator",
    "NavigationLayerComposer",
    "NavigationLayerCompositionContext",
    "NavigationTransitionKind",
    "PageRoute",
    "EmptyTransitionSpec",
    "Route",
    "EntryLifecycle",
    "RouteStackEntry",
    "RouteStackRuntime",
    "TransitionState",
    "TransitionLifecycle",
    "TransitionEngine",
    "TransitionMotionPreset",
    "TransitionMotions",
    "TransitionPhase",
    "TransitionSpec",
    "Transitions",
]
