"""Navigation: a stack of screens, each moving with its own transition."""

from nuiitivet.navigation.navigator import Navigator  # noqa: F401
from nuiitivet.navigation.layer_composer import (
    NavigationLayerComposer,
    NavigationLayerCompositionContext,
    NavigationTransitionKind,
)
from nuiitivet.navigation.protocols import NavigatorProtocol

__all__ = [
    "NavigationLayerComposer",
    "NavigationLayerCompositionContext",
    "NavigationTransitionKind",
    "NavigatorProtocol",
]
