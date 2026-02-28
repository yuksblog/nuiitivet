"""Material Design 3 Divider widget."""

from __future__ import annotations

import logging
from typing import Literal, Optional, Tuple, Union

from nuiitivet.material.styles.divider_style import DividerStyle
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.rendering.skia import make_paint, make_rect
from nuiitivet.theme.manager import manager as theme_manager
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


class Divider(Widget):
    """Material Design 3 Divider widget.

    Renders a thin horizontal or vertical line to visually separate content.
    The line color defaults to the M3 ``outlineVariant`` color role.
    Insets are configured via :class:`~nuiitivet.material.styles.divider_style.DividerStyle`.
    """

    def __init__(
        self,
        *,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[DividerStyle] = None,
    ) -> None:
        """Initialize Divider.

        Args:
            orientation: Direction of the divider. ``"horizontal"`` (default) draws
                a full-width line; ``"vertical"`` draws a full-height line.
            width: Width sizing override. Defaults to ``Sizing.flex()`` for
                horizontal orientation, or ``Sizing.fixed(thickness)`` for vertical.
            height: Height sizing override. Defaults to ``Sizing.fixed(thickness)``
                for horizontal orientation, or ``Sizing.flex()`` for vertical.
            padding: Padding around the divider line.
            style: Optional :class:`~nuiitivet.material.styles.divider_style.DividerStyle`
                override. Falls back to the default ``DividerStyle`` when ``None``.
        """
        effective_style = style or DividerStyle()
        thickness = effective_style.thickness

        resolved_width: SizingLike
        resolved_height: SizingLike

        if width is None:
            resolved_width = Sizing.fixed(thickness) if orientation == "vertical" else Sizing.flex()
        else:
            resolved_width = width

        if height is None:
            resolved_height = Sizing.fixed(thickness) if orientation == "horizontal" else Sizing.flex()
        else:
            resolved_height = height

        super().__init__(width=resolved_width, height=resolved_height, padding=padding)
        self._style = effective_style
        self._orientation = orientation

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size based on orientation and thickness.

        Args:
            max_width: Optional maximum width constraint.
            max_height: Optional maximum height constraint.

        Returns:
            Tuple of ``(width, height)`` in pixels.
        """
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        pref_w = int(w_dim.value) if w_dim.kind == "fixed" else (int(max_width) if max_width is not None else 0)
        pref_h = int(h_dim.value) if h_dim.kind == "fixed" else (int(max_height) if max_height is not None else 0)

        return (pref_w, pref_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint the divider line.

        Args:
            canvas: Skia canvas to paint on.
            x: Left coordinate of the allocated rect.
            y: Top coordinate of the allocated rect.
            width: Width of the allocated rect in pixels.
            height: Height of the allocated rect in pixels.
        """
        self.set_last_rect(x, y, width, height)
        if canvas is None:
            return

        style = self._style

        if self._orientation == "horizontal":
            dx = x + style.inset_left
            dy = y
            dw = max(0, width - style.inset_left - style.inset_right)
            dh = height
        else:
            dx = x
            dy = y + style.inset_left
            dw = width
            dh = max(0, height - style.inset_left - style.inset_right)

        if dw <= 0 or dh <= 0:
            return

        rgba = resolve_color_to_rgba(style.color, theme=theme_manager.current)
        if rgba is None:
            return
        r, g, b, a = rgba

        paint = make_paint(color=(r, g, b, a), style="fill", aa=False)
        if paint is None:
            return

        rect = make_rect(dx, dy, dw, dh)
        if rect is None:
            return

        canvas.drawRect(rect, paint)
