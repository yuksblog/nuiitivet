from dataclasses import dataclass
from typing import Optional
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..theme.types import ColorSpec
from ..widgets.box import Box, ModifierBox


@dataclass
class BorderModifier(ModifierElement):
    color: Optional[ColorSpec]
    width: float = 0.0

    def apply(self, widget: Widget) -> Widget:
        if isinstance(widget, Box):
            widget.border_color = self.color
            widget.border_width = self.width
            return widget

        if isinstance(widget, ModifierBox):
            box = ModifierBox(
                child=widget.children[0] if widget.children else None,
                width=widget.width_sizing,
                height=widget.height_sizing,
                padding=widget.padding,
                modifier=widget._modifier_chain,
                background_color=widget.bgcolor,
                border_width=self.width,
                border_color=self.color,
                corner_radius=widget.corner_radius,
                shadow_blur=widget.shadow_blur,
                shadow_color=widget.shadow_color,
                shadow_offset=widget.shadow_offset,
                alignment=widget.alignment,
            )
            box.clip_content = widget.clip_content
            return box

        return ModifierBox(
            child=widget,
            border_width=self.width,
            border_color=self.color,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def border(color: Optional[ColorSpec], width: float = 0.0) -> BorderModifier:
    return BorderModifier(color=color, width=width)
