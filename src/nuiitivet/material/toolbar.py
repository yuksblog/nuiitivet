"""Material Design 3 toolbar widgets."""

from __future__ import annotations

from typing import Literal, Optional, Sequence, Tuple, Union

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import Button, Fab, IconButton, IconToggleButton, ToggleButton
from nuiitivet.material.styles.toolbar_style import ToolbarStyle
from nuiitivet.modifiers.tooltip import TooltipBox
from nuiitivet.rendering.padding import PaddingLike, parse_padding
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.theme.theme import Theme
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import Widget

_ToolbarOrientation = Literal["horizontal", "vertical"]


def _push_button_styles(style: ToolbarStyle, children: Sequence[Widget]) -> None:
    """Push the scheme's button styles onto the Material buttons among ``children``.

    A tooltip-wrapped button is reached through its wrapper, since icon-only
    toolbar buttons need tooltips. Any other widget is left alone.
    """
    for child in children:
        target = child
        if isinstance(target, TooltipBox):
            wrapped = target.children_snapshot()
            target = wrapped[0] if wrapped else target
        if isinstance(target, Fab):
            target._set_host_style(style.fab_style())
        elif isinstance(target, IconToggleButton):
            target._set_host_style(style.icon_toggle_button_style())
        elif isinstance(target, ToggleButton):
            target._set_host_style(style.toggle_button_style())
        elif isinstance(target, IconButton):
            target._set_host_style(style.icon_button_style())
        elif isinstance(target, Button):
            target._set_host_style(style.button_style())


def _resolve_content_insets(
    style: ToolbarStyle,
    buttons: Sequence[Widget],
) -> tuple[int, int, int, int]:
    """Resolve content padding with a shared edge-inset rule.

    Edge inset is derived from container height and the maximum measured button
    extent, and then applied uniformly for both orientations.
    """
    left, top, right, bottom = style.content_insets
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
    its own.
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

    Edge-to-edge by default: ``padding`` is 0 unless the caller sets it.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        style: Optional[ToolbarStyle] = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> None:
        """Initialize DockedToolbar.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
                A Material button without an explicit style, tooltip-wrapped
                or not, takes the colours the toolbar's colour scheme
                prescribes; a button with one keeps it.
            style: Optional toolbar style. Defaults to the theme's toolbar
                style, which itself falls back to ``ToolbarStyle.standard()``.
            padding: Insets from the allocated rect to the toolbar.
            key: Stable widget identity for dev-bridge targeting and hot reload.
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
            width="wt",
            gap=effective_style.item_gap,
            main_alignment="space-between",
            cross_alignment="center",
            padding=effective_style.content_insets,
        )

        # The container height is MD3-fixed, so the fixed sizing carries the padding band.
        _l, pad_top, _r, pad_bottom = parse_padding(padding if padding is not None else 0)
        super().__init__(
            child=self._content,
            height=effective_style.container_height + pad_top + pad_bottom,
            padding=padding,
            background_color=effective_style.background,
            border_color=effective_style.border_color,
            border_width=effective_style.border_width,
            corner_radius=effective_style.corner_radius,
            alignment="center",
            key=key,
        )

    def _apply_toolbar_style(self, style: ToolbarStyle) -> None:
        super()._apply_toolbar_style(style)
        self.height_sizing = Sizing.fixed(int(style.container_height) + self.padding[1] + self.padding[3])
        self.bgcolor = style.background
        self.border_color = style.border_color
        self.border_width = style.border_width
        self.corner_radius = style.corner_radius
        self._content.gap = style.item_gap
        self._content.padding = style.content_insets
        _push_button_styles(style, self._content.children_snapshot())
        self.invalidate()


class _FloatingToolbarBase(_ToolbarBase):
    """Shared behavior for floating toolbars.

    Floating toolbar exposes external padding to place the floating container
    away from edges. Orientation is fixed by the concrete subclass, which
    selects a Row or Column layout for the action buttons. An optional FAB
    sits trailing, after the container along the same axis.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        fab: Optional[Fab] = None,
        orientation: _ToolbarOrientation,
        padding: PaddingLike = 0,
        style: Optional[ToolbarStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        """Initialize shared floating toolbar state.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
                A Material button without an explicit style, tooltip-wrapped
                or not, takes the colours the toolbar's colour scheme
                prescribes; a button with one keeps it.
            fab: FAB placed trailing, ``fab_gap`` of the style away from the
                container. A FAB without an explicit style takes the colour
                and elevation the toolbar's colour scheme prescribes; a FAB
                with one keeps it.
            orientation: Layout orientation for action buttons, fixed by the subclass.
            padding: External padding around the floating toolbar and its FAB.
            style: Optional toolbar style. Defaults to the theme's toolbar
                style, which itself falls back to ``ToolbarStyle.standard()``.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        self._user_style = style
        self._applied_style = None
        self.orientation = orientation
        self._fab = fab
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
                padding=effective_style.content_insets,
            )
            inner_height: SizingLike = effective_style.container_height
        else:
            layout_content = Column(
                layout_children,
                gap=effective_style.item_gap,
                main_alignment="center",
                cross_alignment="center",
                padding=effective_style.content_insets,
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

        outer_child: Widget = self._inner_container
        self._fab_layout: Optional[Union[Row, Column]] = None
        if fab is not None:
            pair: list[Widget] = [self._inner_container, fab]
            if orientation == "horizontal":
                self._fab_layout = Row(pair, gap=effective_style.fab_gap, cross_alignment="center")
            else:
                self._fab_layout = Column(pair, gap=effective_style.fab_gap, cross_alignment="center")
            outer_child = self._fab_layout

        super().__init__(
            child=outer_child,
            padding=padding,
            background_color=None,
            border_width=0.0,
            corner_radius=0,
            alignment="center",
            key=key,
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
        # Styles go on before the inset is measured, so the buttons are
        # measured once, in their toolbar colours.
        buttons = self._layout_content.children_snapshot()
        _push_button_styles(style, buttons)
        self._layout_content.padding = _resolve_content_insets(style, buttons)
        if self._fab_layout is not None:
            self._fab_layout.gap = style.fab_gap
        if self._fab is not None:
            self._fab._set_host_style(style.fab_style())
        self.invalidate()


class HorizontalFloatingToolbar(_FloatingToolbarBase):
    """Material Design 3 horizontal floating toolbar.

    Lays out action buttons in a row inside a fully rounded floating container.
    An optional FAB sits to the right of the container.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        fab: Optional[Fab] = None,
        padding: PaddingLike = 0,
        style: Optional[ToolbarStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        """Initialize HorizontalFloatingToolbar.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
                A Material button without an explicit style, tooltip-wrapped
                or not, takes the colours the toolbar's colour scheme
                prescribes; a button with one keeps it.
            fab: FAB placed to the right of the container, ``fab_gap`` of the
                style away. A FAB without an explicit style takes the colour
                and elevation the toolbar's colour scheme prescribes; a FAB
                with one keeps it.
            padding: External padding around the floating toolbar and its FAB.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(buttons, fab=fab, orientation="horizontal", padding=padding, style=style, key=key)


class VerticalFloatingToolbar(_FloatingToolbarBase):
    """Material Design 3 vertical floating toolbar.

    Lays out action buttons in a column inside a fully rounded floating container.
    An optional FAB sits below the container.
    """

    def __init__(
        self,
        buttons: Sequence[Widget],
        *,
        fab: Optional[Fab] = None,
        padding: PaddingLike = 0,
        style: Optional[ToolbarStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        """Initialize VerticalFloatingToolbar.

        Args:
            buttons: Widgets placed inside the toolbar. Prefer ``Button`` or
                ``IconButton``; other widgets (including tooltip-wrapped buttons)
                are laid out as-is, but the edge-inset heuristic assumes
                button-sized children and degrades gracefully for larger ones.
                A Material button without an explicit style, tooltip-wrapped
                or not, takes the colours the toolbar's colour scheme
                prescribes; a button with one keeps it.
            fab: FAB placed below the container, ``fab_gap`` of the style
                away. A FAB without an explicit style takes the colour and
                elevation the toolbar's colour scheme prescribes; a FAB with
                one keeps it.
            padding: External padding around the floating toolbar and its FAB.
            style: Optional toolbar style. Defaults to ``ToolbarStyle.standard()``.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(buttons, fab=fab, orientation="vertical", padding=padding, style=style, key=key)


__all__ = ["DockedToolbar", "HorizontalFloatingToolbar", "VerticalFloatingToolbar"]
