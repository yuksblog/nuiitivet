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
        if isinstance(widget, Box):
            self._apply_to_box(widget)
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
