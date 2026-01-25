from dataclasses import dataclass
from typing import Literal
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..layout.scroller import Scroller
from ..scrolling import ScrollDirection
from ..rendering.sizing import Sizing


@dataclass
class ScrollModifier(ModifierElement):
    axis: Literal["x", "y"] = "y"
    show_scrollbar: bool = True

    def apply(self, widget: Widget) -> Widget:
        direction = ScrollDirection.VERTICAL if self.axis == "y" else ScrollDirection.HORIZONTAL
        return Scroller(
            child=widget,
            direction=direction,
            scrollbar_enabled=self.show_scrollbar,
            width=Sizing.flex(),
            height=Sizing.flex(),
        )


def scrollable(axis: Literal["x", "y"] = "y", show_scrollbar: bool = True) -> ScrollModifier:
    return ScrollModifier(axis=axis, show_scrollbar=show_scrollbar)
