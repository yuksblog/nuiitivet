"""Material Design 3 toolbar widgets."""

from __future__ import annotations

from typing import Literal, Optional, Sequence, Tuple, Union

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.styles.toolbar_style import ToolbarStyle
from nuiitivet.rendering.padding import PaddingLike
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.theme.theme import Theme
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


class _ToolbarBase(Box):
    """Shared theme plumbing for the Material toolbars.

    A toolbar has no ``build()``, so it reads the theme where the style is
    consumed -- :meth:`preferred_size`. The read registers a dependency, so a
    theme change re-measures the toolbar and lands back here with the new
    value; the container properties pushed onto :class:`Box` are therefore a
    write-through cache of that pull rather than a value that can go stale on
    its own. See ``docs/design/THEME_CONSUMPTION.md``.
    """

    #: The style the caller passed, or ``None`` to follow the theme.
    _user_style: Optional[ToolbarStyle]
    #: The last style pushed onto the container, or ``None`` before the first
    #: measure -- which is what forces the first application to run even when
    #: the theme resolves to the very preset the constructor already used.
    _applied_style: Optional[ToolbarStyle]

    def _resolve_style(self) -> ToolbarStyle:
        """Return the explicit style, else the one carried by the theme."""
        if self._user_style is not None:
            return self._user_style
        return ToolbarStyle.from_theme(Theme.of(self))

    @property
    def style(self) -> ToolbarStyle:
        """Return the toolbar style currently in effect, pulled from the theme."""
        style = self._resolve_style()
        if style != self._applied_style:
            self._apply_toolbar_style(style)
        return style

    def _apply_toolbar_style(self, style: ToolbarStyle) -> None:
        """Push ``style`` onto the container visuals.

        Subclasses must call ``super()`` so ``_applied_style`` stays in step
        with what was pushed.
        """
        self._applied_style = style

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        # Reading ``style`` is the theme pull, and re-applies it if it moved.
        self.style
        return super().preferred_size(max_width=max_width, max_height=max_height)


class DockedToolbar(_ToolbarBase):
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
            style: Optional toolbar style. Defaults to the theme's toolbar
                style, which itself falls back to ``ToolbarStyle.standard()``.
        """
        self._user_style = style
        self._applied_style = None
        # Read the preset directly rather than through ``self.style``: the theme
        # is unreachable until the widget is attached. The preset is what
        # ``ToolbarStyle.from_theme`` falls back to, so an unthemed app sees no
        # change; a themed one adopts its style on the first measure.
        effective_style = style if style is not None else ToolbarStyle.preset()
        row_children: list[Widget] = list(buttons)

        self._content = Row(
            row_children,
            width="100%",
            gap=effective_style.item_gap,
            main_alignment="space-between",
            cross_alignment="center",
            padding=effective_style.content_padding,
        )

        super().__init__(
            child=self._content,
            height=effective_style.container_height,
            padding=0,
            background_color=effective_style.background,
            border_color=effective_style.border_color,
            border_width=effective_style.border_width,
            corner_radius=effective_style.corner_radius,
            alignment="center",
        )

    def _apply_toolbar_style(self, style: ToolbarStyle) -> None:
        super()._apply_toolbar_style(style)
        self.height_sizing = Sizing.fixed(int(style.container_height))
        self.bgcolor = style.background
        self.border_color = style.border_color
        self.border_width = style.border_width
        self.corner_radius = style.corner_radius
        self._content.gap = style.item_gap
        self._content.padding = style.content_padding
        self.invalidate()


class _FloatingToolbarBase(_ToolbarBase):
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
            style: Optional toolbar style. Defaults to the theme's toolbar
                style, which itself falls back to ``ToolbarStyle.standard()``.
        """
        self._user_style = style
        self._applied_style = None
        self.orientation = orientation
        # Read the preset directly rather than through ``self.style``: the theme
        # is unreachable until the widget is attached. The preset is what
        # ``ToolbarStyle.from_theme`` falls back to, so an unthemed app sees no
        # change; a themed one adopts its style on the first measure.
        effective_style = style if style is not None else ToolbarStyle.preset()
        layout_children: list[Widget] = list(buttons)

        if orientation == "horizontal":
            layout_content: Union[Row, Column] = Row(
                layout_children,
                gap=effective_style.item_gap,
                main_alignment="center",
                cross_alignment="center",
                padding=effective_style.content_padding,
            )
            inner_height: SizingLike = effective_style.container_height
        else:
            layout_content = Column(
                layout_children,
                gap=effective_style.item_gap,
                main_alignment="center",
                cross_alignment="center",
                padding=effective_style.content_padding,
            )
            inner_height = None

        self._layout_content = layout_content

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

    def _apply_toolbar_style(self, style: ToolbarStyle) -> None:
        """Push ``style`` onto the inner container and re-derive the edge inset.

        The inset comes from the buttons' preferred sizes, so this cannot run
        from ``__init__``: it would measure buttons that are not attached to
        anything yet. The first :meth:`preferred_size` is early enough -- the
        inset is only consumed by layout, which cannot precede it.
        """
        super()._apply_toolbar_style(style)
        self._inner_container.bgcolor = style.background
        self._inner_container.border_color = style.border_color
        self._inner_container.border_width = style.border_width
        if self.orientation == "horizontal":
            self._inner_container.height_sizing = Sizing.fixed(int(style.container_height))
        self._layout_content.gap = style.item_gap
        self._layout_content.padding = _resolve_content_padding(
            style,
            self._layout_content.children_snapshot(),
        )
        self.invalidate()


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
