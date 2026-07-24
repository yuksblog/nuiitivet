"""Material Design 3 toolbar widgets."""

from __future__ import annotations

from typing import Literal, Optional, Sequence

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.styles.toolbar_style import ToolbarStyle
from nuiitivet.rendering.padding import PaddingLike
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import Widget

_ToolbarOrientation = Literal["horizontal", "vertical"]


def _resolve_content_padding(
    style: ToolbarStyle,
    buttons: Sequence[Widget],
) -> tuple[int, int, int, int]:
    """Resolve content padding with a shared edge-inset rule.

    Edge inset is derived from container height and the maximum measured button
    extent, and then applied uniformly for both orientations.
    """
    left, top, right, bottom = style.content_padding
    max_extent = 0
    for button in buttons:
        width, height = measure_preferred_size(button)
        max_extent = max(max_extent, int(width), int(height))

    edge_inset = max(0, (int(style.container_height) - int(max_extent)) // 2)
    return (
        max(int(left), edge_inset),
        max(int(top), edge_inset),
        max(int(right), edge_inset),
        max(int(bottom), edge_inset),
    )


class DockedToolbar(Box):
    """Material Design 3 docked toolbar.

    This toolbar is edge-to-edge and therefore does not expose external padding.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        style: Optional[ToolbarStyle] = None,
    ) -> None:
        """Initialize DockedToolbar.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
        """
        self._user_style = style
        effective_style = self.style
        row_children: list[Widget] = list(buttons)

        content = Row(
            row_children,
            width="100%",
            gap=effective_style.item_gap,
            main_alignment="space-between",
            cross_alignment="center",
            padding=effective_style.content_padding,
        )

        super().__init__(
            child=content,
            height=effective_style.container_height,
            padding=0,
            background_color=effective_style.background,
            border_color=effective_style.border_color,
            border_width=effective_style.border_width,
            corner_radius=effective_style.corner_radius,
            alignment="center",
        )

    @property
    def style(self) -> ToolbarStyle:
        """Return toolbar style from explicit style or default style."""
        return self._user_style if self._user_style is not None else ToolbarStyle.standard()


class _FloatingToolbarBase(Box):
    """Shared behavior for floating toolbars.

    Floating toolbar exposes external padding to place the floating container
    away from edges. Orientation is fixed by the concrete subclass, which
    selects a Row or Column layout for the action buttons.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        orientation: _ToolbarOrientation,
        padding: PaddingLike = 0,
        style: Optional[ToolbarStyle] = None,
    ) -> None:
        """Initialize shared floating toolbar state.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
            orientation: Layout orientation for action buttons, fixed by the subclass.
            padding: External padding around the floating toolbar.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
        """
        self._user_style = style
        self.orientation = orientation
        effective_style = self.style
        layout_children: list[Widget] = list(buttons)
        content_padding = _resolve_content_padding(effective_style, layout_children)

        if orientation == "horizontal":
            layout_content: Widget = Row(
                layout_children,
                gap=effective_style.item_gap,
                main_alignment="center",
                cross_alignment="center",
                padding=content_padding,
            )
            inner_height: SizingLike = effective_style.container_height
        else:
            layout_content = Column(
                layout_children,
                gap=effective_style.item_gap,
                main_alignment="center",
                cross_alignment="center",
                padding=content_padding,
            )
            inner_height = None

        # Floating toolbar shape is always fully rounded per spec intent.
        inner_corner_radius = 9999
        self._inner_container = Box(
            child=layout_content,
            height=inner_height,
            padding=0,
            background_color=effective_style.background,
            border_color=effective_style.border_color,
            border_width=effective_style.border_width,
            corner_radius=inner_corner_radius,
            alignment="center",
        )

        super().__init__(
            child=self._inner_container,
            padding=padding,
            background_color=None,
            border_width=0.0,
            corner_radius=0,
            alignment="center",
        )

    @property
    def style(self) -> ToolbarStyle:
        """Return toolbar style from explicit style or default style."""
        return self._user_style if self._user_style is not None else ToolbarStyle.standard()


class HorizontalFloatingToolbar(_FloatingToolbarBase):
    """Material Design 3 horizontal floating toolbar.

    Lays out action buttons in a row inside a fully rounded floating container.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        padding: PaddingLike = 0,
        style: Optional[ToolbarStyle] = None,
    ) -> None:
        """Initialize HorizontalFloatingToolbar.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
            padding: External padding around the floating toolbar.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
        """
        super().__init__(buttons, orientation="horizontal", padding=padding, style=style)


class VerticalFloatingToolbar(_FloatingToolbarBase):
    """Material Design 3 vertical floating toolbar.

    Lays out action buttons in a column inside a fully rounded floating container.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        padding: PaddingLike = 0,
        style: Optional[ToolbarStyle] = None,
    ) -> None:
        """Initialize VerticalFloatingToolbar.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
            padding: External padding around the floating toolbar.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
        """
        super().__init__(buttons, orientation="vertical", padding=padding, style=style)


__all__ = ["DockedToolbar", "HorizontalFloatingToolbar", "VerticalFloatingToolbar"]
