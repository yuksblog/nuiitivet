from dataclasses import dataclass
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..theme.types import ColorSpec
from ..widgets.box import Box, ModifierBox


@dataclass
class BackgroundModifier(ModifierElement):
    color: ColorSpec

    def apply(self, widget: Widget) -> Widget:
        if isinstance(widget, Box):
            widget.bgcolor = self.color
            return widget

        if isinstance(widget, ModifierBox):
            box = ModifierBox(
                child=widget.children[0] if widget.children else None,
                width=widget.width_sizing,
                height=widget.height_sizing,
                padding=widget.padding,
                modifier=widget._modifier_chain,
                background_color=self.color,
                border_width=widget.border_width,
                border_color=widget.border_color,
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
            background_color=self.color,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def background(color: ColorSpec) -> BackgroundModifier:
    return BackgroundModifier(color)
