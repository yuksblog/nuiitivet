from dataclasses import dataclass
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.box import Box, ModifierBox


@dataclass
class ClipModifier(ModifierElement):
    def apply(self, widget: Widget) -> Widget:
        if isinstance(widget, Box):
            widget.clip_content = True
            return widget

        # Wrap in a ModifierBox that clips. The wrapper must inherit the child's
        # sizing, otherwise a weight/fixed request collapses into auto and the box
        # grows to the content's natural size.
        box = ModifierBox(
            child=widget,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )
        box.clip_content = True
        return box


def clip() -> ClipModifier:
    return ClipModifier()
