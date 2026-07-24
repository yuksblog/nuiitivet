"""Material Design 3 Divider widgets."""

from __future__ import annotations

import logging
from typing import Literal, Optional, Tuple

from nuiitivet.material.styles.divider_style import DividerStyle
from nuiitivet.rendering.padding import PaddingLike, parse_padding
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.rendering.skia import make_paint, make_rect
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


class _DividerBase(Widget):
    """Shared behavior for divider widgets.

    Renders a thin line to visually separate content. The line color defaults
    to the M3 ``outlineVariant`` color role. Insets are configured via
    :class:`~nuiitivet.material.styles.divider_style.DividerStyle`.

    Orientation is fixed by the concrete subclass; the cross-axis (thickness)
    sizing is derived from the style, and only the main-axis size is exposed.
    """

    def __init__(
        self,
        *,
        orientation: Literal["horizontal", "vertical"],
        width: SizingLike,
        height: SizingLike,
        padding: PaddingLike,
        style: Optional[DividerStyle],
    ) -> None:
        """Initialize shared divider state.

        Args:
            orientation: Direction of the divider, fixed by the subclass.
            width: Resolved width sizing.
            height: Resolved height sizing.
            padding: Padding around the divider line.
            style: Resolved divider style.
        """
        effective_style = style or DividerStyle()
        super().__init__(width=width, height=height, padding=padding)
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

        # The fixed cross-axis sizing already bakes in this-axis padding (see
        # the concrete subclass), so it is returned as-is — adding padding again
        # here would double-count it and over-report the size to parent layouts.
        # Flex dimensions fill the available constraint; the line is then inset
        # within the padded box via ``content_rect`` at paint time.
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
        thickness = style.thickness

        # Draw inside the padded content rect so that padding produces real
        # margins around the line (the line keeps its 1dp thickness and is
        # centred on the cross axis if the content box is taller/wider).
        cx, cy, cw, ch = self.content_rect(x, y, width, height)

        if self._orientation == "horizontal":
            line_h = min(thickness, ch) if ch > 0 else thickness
            dx = cx + style.inset_left
            dy = cy + max(0, (ch - line_h) // 2)
            dw = max(0, cw - style.inset_left - style.inset_right)
            dh = line_h
        else:
            line_w = min(thickness, cw) if cw > 0 else thickness
            dx = cx + max(0, (cw - line_w) // 2)
            dy = cy + style.inset_left
            dw = line_w
            dh = max(0, ch - style.inset_left - style.inset_right)

        if dw <= 0 or dh <= 0:
            return

        from nuiitivet.theme.theme import Theme

        rgba = resolve_color_to_rgba(style.color, theme=Theme.of(self))
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


def _cross_axis_thickness(style: Optional[DividerStyle], pad_a: int, pad_b: int) -> Sizing:
    """Return the fixed cross-axis sizing including cross-axis padding.

    Row/Column size fixed-dimension children directly from their sizing value
    (not ``preferred_size``), so padding baked only into ``preferred_size``
    would be ignored and produce no visible margin.
    """
    effective_style = style or DividerStyle()
    return Sizing.fixed(effective_style.thickness + pad_a + pad_b)


class HorizontalDivider(_DividerBase):
    """Material Design 3 horizontal divider.

    Draws a full-width line to separate content. Only ``width`` is exposed;
    the height (thickness) is derived from the style.
    """

    def __init__(
        self,
        *,
        width: SizingLike = None,
        padding: PaddingLike = 0,
        style: Optional[DividerStyle] = None,
    ) -> None:
        """Initialize HorizontalDivider.

        Args:
            width: Width sizing override. Defaults to ``Sizing.flex()``.
            padding: Padding around the divider line.
            style: Optional :class:`~nuiitivet.material.styles.divider_style.DividerStyle`
                override. Falls back to the default ``DividerStyle`` when ``None``.
        """
        _pad_l, pad_t, _pad_r, pad_b = parse_padding(padding)
        resolved_width: SizingLike = Sizing.flex() if width is None else width
        super().__init__(
            orientation="horizontal",
            width=resolved_width,
            height=_cross_axis_thickness(style, pad_t, pad_b),
            padding=padding,
            style=style,
        )


class VerticalDivider(_DividerBase):
    """Material Design 3 vertical divider.

    Draws a full-height line to separate content. Only ``height`` is exposed;
    the width (thickness) is derived from the style.
    """

    def __init__(
        self,
        *,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        style: Optional[DividerStyle] = None,
    ) -> None:
        """Initialize VerticalDivider.

        Args:
            height: Height sizing override. Defaults to ``Sizing.flex()``.
            padding: Padding around the divider line.
            style: Optional :class:`~nuiitivet.material.styles.divider_style.DividerStyle`
                override. Falls back to the default ``DividerStyle`` when ``None``.
        """
        pad_l, _pad_t, pad_r, _pad_b = parse_padding(padding)
        resolved_height: SizingLike = Sizing.flex() if height is None else height
        super().__init__(
            orientation="vertical",
            width=_cross_axis_thickness(style, pad_l, pad_r),
            height=resolved_height,
            padding=padding,
            style=style,
        )


__all__ = ["HorizontalDivider", "VerticalDivider"]
