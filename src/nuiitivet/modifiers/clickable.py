from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import InteractionRegion, VoidCallback, ensure_interaction_region


@dataclass(slots=True)
class ClickableModifier(ModifierElement):
    on_click: Optional[VoidCallback] = None
    any_button: bool = False

    def apply(self, widget: Widget) -> Widget:
        region: InteractionRegion = ensure_interaction_region(widget)
        region.enable_click(on_click=self.on_click, any_button=self.any_button)
        return region


def clickable(on_click: Optional[VoidCallback] = None, *, any_button: bool = False) -> ClickableModifier:
    """Make a widget respond to clicks.

    Args:
        on_click: Callback invoked on a completed click.
        any_button: When ``True``, secondary and middle buttons activate the
            click too. Intended for dismissal surfaces such as an overlay's
            outside-tap layer; ordinary controls should stay primary-only.
    """
    return ClickableModifier(on_click=on_click, any_button=any_button)
