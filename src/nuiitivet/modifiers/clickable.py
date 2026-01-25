from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import InteractionRegion, ensure_interaction_region


@dataclass(slots=True)
class ClickableModifier(ModifierElement):
    on_click: Optional[Callable[[], None]] = None

    def apply(self, widget: Widget) -> Widget:
        region: InteractionRegion = ensure_interaction_region(widget)
        region.enable_click(on_click=self.on_click)
        return region


def clickable(on_click: Optional[Callable[[], None]] = None) -> ClickableModifier:
    return ClickableModifier(on_click=on_click)
