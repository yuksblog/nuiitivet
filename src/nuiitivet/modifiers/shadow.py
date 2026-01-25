from dataclasses import dataclass
from typing import Optional, Tuple
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..theme.types import ColorSpec
from ..widgets.box import Box, ModifierBox


@dataclass
class ShadowModifier(ModifierElement):
    color: Optional[ColorSpec]
    blur: float = 0.0
    offset: Tuple[float, float] = (0.0, 0.0)

    def apply(self, widget: Widget) -> Widget:
        if isinstance(widget, Box):
            widget.shadow_color = self.color
            widget.shadow_blur = self.blur
            widget.shadow_offset = self.offset
            return widget

        if isinstance(widget, ModifierBox):
            box = ModifierBox(
                child=widget.children[0] if widget.children else None,
                width=widget.width_sizing,
                height=widget.height_sizing,
                padding=widget.padding,
                modifier=widget._modifier_chain,
                background_color=widget.bgcolor,
                border_width=widget.border_width,
                border_color=widget.border_color,
                corner_radius=widget.corner_radius,
                shadow_blur=self.blur,
                shadow_color=self.color,
                shadow_offset=self.offset,
                alignment=widget.alignment,
            )
            box.clip_content = widget.clip_content
            return box

        return ModifierBox(
            child=widget,
            shadow_blur=self.blur,
            shadow_color=self.color,
            shadow_offset=self.offset,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def shadow(
    color: Optional[ColorSpec],
    blur: float = 0.0,
    offset: Tuple[float, float] = (0.0, 0.0),
) -> ShadowModifier:
    return ShadowModifier(color=color, blur=blur, offset=offset)
