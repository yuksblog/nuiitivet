from typing import Callable, Optional

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import FocusNode, ensure_interaction_region


class FocusableModifier(ModifierElement):
    def __init__(
        self,
        enabled: bool = True,
        on_focus_change: Optional[Callable[[bool], None]] = None,
        on_key: Optional[Callable[[str, int], bool]] = None,
    ) -> None:
        self.enabled = enabled
        self.on_focus_change = on_focus_change
        self.on_key = on_key

    def apply(self, widget: Widget) -> Widget:
        if not self.enabled:
            return widget

        region = ensure_interaction_region(widget)

        # Check if FocusNode already exists
        # Note: ensure_interaction_region might return an existing region which already has a FocusNode
        existing_node = region.get_node(FocusNode)
        if existing_node is None:
            node = FocusNode(
                on_focus_change=self.on_focus_change,
                on_key=self.on_key,
            )
            region.add_node(node)
        else:
            # If a FocusNode already exists, we might want to update it or chain callbacks.
            # For this initial implementation, we'll assume the first one wins or
            # we simply don't support multiple focusable modifiers on the same widget effectively yet.
            # However, to support "Button(focusable=True)" which internally uses focusable(),
            # and then user adds ".focusable(on_key=...)", we might need to handle this.
            # For now, let's just add a new node if we want to support multiple behaviors,
            # but FocusNode logic assumes one focus per region usually.
            # Let's stick to "one FocusNode per InteractionRegion" for simplicity in Phase 1.
            pass

        return region


def focusable(
    enabled: bool = True,
    on_focus_change: Optional[Callable[[bool], None]] = None,
    on_key: Optional[Callable[[str, int], bool]] = None,
) -> FocusableModifier:
    """
    Mark the widget as focusable.

    Args:
        enabled: Whether the widget is focusable.
        on_focus_change: Callback invoked when focus state changes.
        on_key: Callback invoked when a key event occurs while focused.
                Return True to stop propagation (bubbling).
    """
    return FocusableModifier(enabled, on_focus_change, on_key)
