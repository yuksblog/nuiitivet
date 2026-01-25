"""Base button implementation (design-agnostic)."""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import ObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia.color import make_opacity_paint
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.clickable import Clickable

logger = logging.getLogger(__name__)


class ButtonBase(Clickable):
    """
    Base class for buttons.
    Handles common button behavior:
    - Interaction (via Clickable)
    - Disabled state opacity
    - Basic structure (Background -> Overlay Hook -> Children -> Border)
    """

    def __init__(
        self,
        child: Widget,
        on_click: Optional[Callable[[], None]] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int, int, int]] = 0,
        disabled: bool | ObservableProtocol[bool] = False,
        disabled_opacity: float = 0.38,
        **kwargs,
    ):
        super().__init__(
            child=child,
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            **kwargs,
        )
        self.disabled_opacity = disabled_opacity

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        disabled_layer_applied = False
        if self.disabled:
            try:
                opacity_paint = make_opacity_paint(self.disabled_opacity)
                if opacity_paint is not None:
                    canvas.saveLayer(None, opacity_paint)
                    disabled_layer_applied = True
            except Exception:
                exception_once(logger, "button_apply_disabled_layer_exc", "Failed to apply disabled opacity layer")

        try:
            self.set_last_rect(x, y, width, height)
            self.draw_background(canvas, x, y, width, height)
            self.draw_overlay(canvas, x, y, width, height)
            self.draw_children(canvas, x, y, width, height)
            self.draw_border(canvas, x, y, width, height)
        finally:
            if disabled_layer_applied:
                try:
                    canvas.restore()
                except Exception:
                    exception_once(logger, "button_restore_layer_exc", "Failed to restore disabled opacity layer")

    def draw_overlay(self, canvas, x: int, y: int, width: int, height: int):
        """Hook for drawing visual feedback (e.g. state layer, ripple).

        Subclasses (like MaterialButtonBase) should override this to provide
        design-system specific feedback.
        """
        pass
