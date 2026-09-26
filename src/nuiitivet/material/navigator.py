"""Material-specific navigator defaults."""

from __future__ import annotations

from nuiitivet.navigation.layer_composer import NavigationLayerComposer
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.transition.spec import TransitionSpec
from nuiitivet.widgeting.widget import Widget

from .navigation_visual_state import MaterialNavigationLayerComposer
from .transition_spec import MaterialTransitions


class MaterialNavigator(Navigator):
    """Navigator whose screens default to the Material page transition.

    It also paints transitions with the Material layer composer, so
    :meth:`Navigator.routes` and :meth:`Navigator.intents` animate too.
    """

    def __init__(
        self,
        screen: Widget | None = None,
        *,
        transition: TransitionSpec | None = None,
        layer_composer: NavigationLayerComposer | None = None,
        key: str | None = None,
    ) -> None:
        """Initialize a MaterialNavigator with a single initial screen.

        Args:
            screen: The initial screen. ``None`` starts with an empty stack.
            transition: The transition ``screen`` moves with. Defaults to
                ``MaterialTransitions.page()``.
            layer_composer: Optional custom layer composer.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(
            screen,
            transition=transition,
            layer_composer=layer_composer or MaterialNavigationLayerComposer(),
            key=key,
        )

    def _default_transition(self) -> TransitionSpec:
        return MaterialTransitions.page()


__all__ = ["MaterialNavigator"]
