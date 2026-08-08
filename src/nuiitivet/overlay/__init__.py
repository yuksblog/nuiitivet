"""Overlay system for transient layers."""

from .overlay_route import OverlayRoute
from .intent_resolver import IntentResolver
from .overlay_aware import OverlayAware
from .overlay_handle import OverlayHandle
from .overlay import Overlay
from .overlay_entry import OverlayEntry
from .overlay_position import OverlayPosition
from .protocols import OverlayProtocol
from .layer_composer import OverlayLayerComposer, OverlayLayerCompositionContext
from .result import OverlayDismissReason, OverlayResult
from .toast import PlainToast

from .intents import PlainDialogIntent, LoadingDialogIntent

__all__ = [
    "PlainDialogIntent",
    "OverlayRoute",
    "IntentResolver",
    "LoadingDialogIntent",
    "Overlay",
    "OverlayLayerComposer",
    "OverlayLayerCompositionContext",
    "OverlayDismissReason",
    "OverlayAware",
    "OverlayEntry",
    "OverlayHandle",
    "OverlayProtocol",
    "OverlayResult",
    "PlainToast",
    "OverlayPosition",
]
