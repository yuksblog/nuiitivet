"""Navigation primitives.

This package provides a minimal Navigator/Route API.
"""

from nuiitivet.navigation.navigator import Navigator  # noqa: F401
from nuiitivet.navigation.layer_composer import (
    NavigationLayerComposer,
    NavigationLayerCompositionContext,
    NavigationTransitionKind,
)
from nuiitivet.navigation.protocols import NavigatorProtocol
from nuiitivet.navigation.route import Route

__all__ = [
    "NavigationLayerComposer",
    "NavigationLayerCompositionContext",
    "NavigationTransitionKind",
    "NavigatorProtocol",
    "Route",
]
