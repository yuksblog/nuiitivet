"""Design-agnostic contracts for overlay layer composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from nuiitivet.widgeting.widget import Widget

from .transition_state import OverlayTransitionState


@dataclass(frozen=True, slots=True)
class OverlayLayerCompositionContext:
    """Input context for composing a rendered overlay layer.

    A composer *paints*; it never decides where input goes and never stacks the
    layers. Pointer blocking, outside-tap dismissal, hit participation and
    z-order are owned by :meth:`Overlay.show`. Consequently this context carries
    visual facts only.

    Attributes:
        content: Route content widget for the current overlay entry.
        transition_state: Transition lifecycle observables and transition spec token for this entry.
        backdrop: Whether a backdrop should be painted behind the content.
        position_content: Function to place content according to overlay position.
    """

    content: Widget
    transition_state: OverlayTransitionState
    backdrop: bool
    position_content: Callable[[Widget], Widget]


@dataclass(frozen=True, slots=True)
class OverlayLayerPaint:
    """What a composer paints for one overlay entry, as separate layers.

    The two layers are returned side by side rather than pre-stacked, so the
    core can place its own blocking layer between them and mark the backdrop as
    decoration. A composer never has to reason about either.

    Attributes:
        content: The positioned (and possibly animated) content layer.
        backdrop: The layer painted behind the content, or ``None`` when the
            entry was shown with ``backdrop=False``. It is treated as pure
            decoration: the core makes it click-through, so it never catches a
            pointer event no matter what it paints.
    """

    content: Widget
    backdrop: Widget | None = None


class OverlayLayerComposer(Protocol):
    """Composable boundary for visual overlay layer rendering."""

    def compose(self, context: OverlayLayerCompositionContext) -> OverlayLayerPaint:
        """Paint the layers for an overlay entry from its visual facts."""


__all__ = ["OverlayLayerComposer", "OverlayLayerCompositionContext", "OverlayLayerPaint"]
