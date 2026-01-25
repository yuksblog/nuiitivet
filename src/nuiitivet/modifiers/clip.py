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

        # Wrap in a ModifierBox that clips
        box = ModifierBox(child=widget)
        box.clip_content = True
        return box


def clip() -> ClipModifier:
    return ClipModifier()
