"""Material Design 3 toolbar widgets."""

from __future__ import annotations

from typing import Literal, Optional, Sequence, Union

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import MaterialButtonBase
from nuiitivet.material.styles.toolbar_style import ToolbarStyle
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.widgets.box import Box

PaddingLike = Union[int, tuple[int, int], tuple[int, int, int, int]]
ToolbarOrientation = Literal["horizontal", "vertical"]


def _validate_buttons(buttons: Sequence[MaterialButtonBase]) -> list[MaterialButtonBase]:
    normalized = list(buttons)
    for button in normalized:
        if not isinstance(button, MaterialButtonBase):
            raise TypeError("buttons must contain only MaterialButtonBase instances")
    return normalized


def _resolve_content_padding(
    style: ToolbarStyle,
    buttons: Sequence[MaterialButtonBase],
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
        buttons: Sequence[MaterialButtonBase],
        *,
        style: Optional[ToolbarStyle] = None,
    ) -> None:
        """Initialize DockedToolbar.

        Args:
            buttons: Action buttons placed inside the toolbar.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
        """
        self._user_style = style
        effective_style = self.style
        children = _validate_buttons(buttons)

        content = Row(
            children,
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


class FloatingToolbar(Box):
    """Material Design 3 floating toolbar.

    Floating toolbar supports both horizontal and vertical orientations and
    exposes external padding to place the floating container away from edges.
    """

    def __init__(
        self,
        buttons: Sequence[MaterialButtonBase],
        *,
        orientation: ToolbarOrientation = "horizontal",
        padding: PaddingLike = 0,
        style: Optional[ToolbarStyle] = None,
    ) -> None:
        """Initialize FloatingToolbar.

        Args:
            buttons: Action buttons placed inside the toolbar.
            orientation: Layout orientation for action buttons.
            padding: External padding around the floating toolbar.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
        """
        if orientation not in ("horizontal", "vertical"):
            raise ValueError("orientation must be 'horizontal' or 'vertical'")

        self._user_style = style
        self.orientation = orientation
        effective_style = self.style
        children = _validate_buttons(buttons)
        content_padding = _resolve_content_padding(effective_style, children)

        if orientation == "horizontal":
            content = Row(
                children,
                gap=effective_style.item_gap,
                main_alignment="center",
                cross_alignment="center",
                padding=content_padding,
            )
            inner_height: SizingLike = effective_style.container_height
        else:
            content = Column(
                children,
                gap=effective_style.item_gap,
                main_alignment="center",
                cross_alignment="center",
                padding=content_padding,
            )
            inner_height = None

        # Floating toolbar shape is always fully rounded per spec intent.
        inner_corner_radius = 9999
        self._inner_container = Box(
            child=content,
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


__all__ = ["DockedToolbar", "FloatingToolbar", "ToolbarOrientation"]
