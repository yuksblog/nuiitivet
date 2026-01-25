from __future__ import annotations

from typing import Any, Tuple
import logging

from nuiitivet.widgeting.widget import Widget
from nuiitivet.rendering.skia import make_paint
from nuiitivet.theme.types import ColorSpec
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.common.logging_once import exception_once

logger = logging.getLogger(__name__)


class IconBase(Widget):
    """Base class for icon widgets.

    Provides utilities for rendering text blobs centered in the widget area.
    """

    def __init__(self, size: SizingLike = 24, padding: Tuple[int, int, int, int] | Tuple[int, int] | int = 0, **kwargs):
        super().__init__(width=size, height=size, padding=padding, **kwargs)

    def draw_blob(self, canvas: Any, blob: Any, color: ColorSpec, x: int, y: int, width: int, height: int):
        """Draw a text blob centered in the content area."""
        if blob is None:
            return

        cx, cy, cw, ch = self.content_rect(x, y, width, height)

        try:
            bounds = blob.bounds()
            tx = cx + (cw - bounds.width()) / 2 - bounds.left()
            ty = cy + (ch - bounds.height()) / 2 - bounds.top()
        except Exception:
            exception_once(logger, "icon_base_blob_bounds_exc", "Failed to get blob bounds")
            return

        try:
            from nuiitivet.theme.manager import manager as theme_manager

            rgba = resolve_color_to_rgba(color, theme=theme_manager.current)
            paint = make_paint(color=rgba, style="fill", aa=True)
        except Exception:
            exception_once(logger, "icon_base_resolve_color_exc", "Failed to resolve icon color")
            return

        if paint is None:
            return

        try:
            canvas.drawTextBlob(blob, tx, ty, paint)
        except Exception:
            exception_once(logger, "icon_base_draw_text_blob_exc", "drawTextBlob failed")
