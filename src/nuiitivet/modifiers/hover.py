from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import InteractionRegion, ensure_interaction_region


@dataclass(slots=True)
class HoverModifier(ModifierElement):
    on_hover_change: Optional[Callable[[bool], None]] = None

    def apply(self, widget: Widget) -> Widget:
        region: InteractionRegion = ensure_interaction_region(widget)
        region.enable_hover(on_change=self.on_hover_change)
        return region


def hoverable(on_hover_change: Optional[Callable[[bool], None]] = None) -> HoverModifier:
    return HoverModifier(on_hover_change=on_hover_change)
