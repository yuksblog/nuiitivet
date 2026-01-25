import logging
from dataclasses import dataclass
from typing import Union, Tuple

from nuiitivet.common.logging_once import exception_once

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.box import Box, ModifierBox


logger = logging.getLogger(__name__)


@dataclass
class CornerRadiusModifier(ModifierElement):
    radius: Union[float, Tuple[float, float, float, float]]

    def _apply_to_box(self, target: Widget) -> bool:
        if isinstance(target, Box):
            try:
                target.corner_radius = self.radius
                target.clip_content = True
                return True
            except Exception:
                exception_once(logger, "corner_radius_modifier_apply_exc", "Failed to apply corner radius modifier")
                return False
        return False

    def apply(self, widget: Widget) -> Widget:
        self._apply_to_box(widget)
        # Optimization: Always merge with existing ModifierBox
        if isinstance(widget, ModifierBox):
            child = widget.children[0] if widget.children else None
            if child is not None:
                self._apply_to_box(child)
            box = ModifierBox(
                child=child,
                width=widget.width_sizing,
                height=widget.height_sizing,
                padding=widget.padding,
                modifier=widget._modifier_chain,
                # Merged properties (overwrite radius)
                background_color=widget.bgcolor,
                border_width=widget.border_width,
                border_color=widget.border_color,
                corner_radius=self.radius,
                shadow_blur=widget.shadow_blur,
                shadow_color=widget.shadow_color,
                shadow_offset=widget.shadow_offset,
                alignment=widget.alignment,
            )
            box.clip_content = True
            return box

        if isinstance(widget, Box):
            widget.clip_content = True
            return widget

        box = ModifierBox(
            child=widget,
            corner_radius=self.radius,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )
        box.clip_content = True
        return box


def corner_radius(radius: Union[float, Tuple[float, float, float, float]]) -> CornerRadiusModifier:
    return CornerRadiusModifier(radius=radius)
