"""Material Design 3 Navigation Rail.

This module contains the implementation of the Navigation Rail component.
"""

from typing import Callable, Optional, Sequence, Tuple, Union

from nuiitivet.widgeting.widget import Widget
from nuiitivet.rendering.sizing import SizingLike, Sizing
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.text import Text
from nuiitivet.material.icon import Icon
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import InteractionHostMixin, InteractionState
from nuiitivet.material.theme.color_role import ColorRole


class RailItem(Widget):
    """Navigation rail destination item.

    A widget representing a single destination in NavigationRail.
    Displays an icon and optional label (when rail is expanded).
    """

    def __init__(
        self,
        icon: str,
        label: str,
    ) -> None:
        super().__init__()

        if not isinstance(icon, str):
            raise TypeError(f"icon must be str, got {type(icon)}")
        if not isinstance(label, str):
            raise TypeError(f"label must be str, got {type(label)}")

        self.icon_spec = icon
        self.label_spec = label

        self._icon_widget: Widget
        self._label_widget: Widget

        # Create widgets
        from nuiitivet.material.styles.icon_style import IconStyle
        from nuiitivet.material.styles.text_style import TextStyle

        self._icon_widget = Icon(icon, size=24, style=IconStyle(color=ColorRole.ON_SURFACE))
        self._label_widget = Text(
            label,
            style=TextStyle(
                font_size=12,
                text_alignment="center",
                overflow="ellipsis",
            ),
        )

    @property
    def icon_widget(self) -> Widget:
        """Get the icon widget."""
        return self._icon_widget

    @property
    def label_widget(self) -> Widget:
        """Get the label widget."""
        return self._label_widget


class _RailItemButton(InteractionHostMixin, Box):
    """Internal button widget for NavigationRail items."""

    def __init__(
        self,
        rail_item: RailItem,
        selected: bool,
        expanded: bool,
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        from nuiitivet.material.text import Text

        label_widget = rail_item.label_widget
        if isinstance(label_widget, Text):
            style = getattr(label_widget, "_style", None)
            copier = getattr(style, "copy_with", None) if style is not None else None
            if callable(copier):
                if expanded:
                    # Expanded: label should be left/start-aligned.
                    label_widget._style = copier(text_alignment="start", font_size=14)
                    label_widget.width_sizing = Sizing.auto()
                else:
                    # Collapsed: label centered and constrained for ellipsis.
                    label_widget._style = copier(text_alignment="center", font_size=12)
                    label_widget.width_sizing = Sizing.fixed(72)

        child: Widget
        if expanded:
            # Expanded: icon + label horizontally with active indicator on both
            # Active indicator wraps both icon and label
            indicator_content = Row(
                [rail_item.icon_widget, label_widget],
                gap=8,  # M3 spec: 8dp icon-label space
                padding=0,  # No padding inside indicator
                cross_alignment="center",
            )

            # Active indicator (background) - wraps icon + label
            bgcolor = ColorRole.SECONDARY_CONTAINER if selected else None
            indicator = Box(
                child=indicator_content,
                background_color=bgcolor,
                corner_radius=16,  # M3 spec: full rounded
                width=Sizing.auto(),
                height=Sizing.fixed(56),
                padding=(16, 8),  # M3 spec: 16dp leading/trailing, 8dp vertical
            )

            self._indicator_box: Box = indicator

            child = indicator
        else:
            # Collapsed: icon (with indicator) above label, vertically stacked
            # Active indicator only wraps the icon
            bgcolor = ColorRole.SECONDARY_CONTAINER if selected else None
            icon_indicator = Box(
                child=rail_item.icon_widget,
                background_color=bgcolor,
                corner_radius=16,  # M3 spec: full rounded
                width=Sizing.fixed(56),  # M3 spec: 56dp width
                height=Sizing.fixed(32),  # M3 spec: 32dp height
                alignment="center",  # Center icon
            )

            self._indicator_box = icon_indicator

            # Stack indicator and label vertically, both centered
            child = Column(
                [icon_indicator, label_widget],
                gap=4,  # M3 spec: 4dp icon-label space
                cross_alignment="center",  # Center both items
                padding=0,
            )

        super().__init__(
            child=child,
            width=Sizing.auto(),  # Fit content width
            height=Sizing.auto(),  # Fit content height
            padding=(8, 0, 0, 0) if expanded else 0,
        )

        self.on_click_handler = on_click
        self._state = InteractionState(disabled=False)

        # Enable hover and click
        self.enable_hover()
        self.enable_click(on_click=self._handle_click)

    def set_selected(self, selected: bool) -> None:
        bgcolor = ColorRole.SECONDARY_CONTAINER if selected else None
        self._indicator_box.bgcolor = bgcolor
        self._state.selected = bool(selected)

    def _handle_click(self) -> None:
        """Handle click event."""
        if self.on_click_handler is not None:
            self.on_click_handler()


class NavigationRail(Widget):
    """Vertical navigation bar for desktop applications.

    Material Design 3 component for persistent side navigation.
    Replaces NavigationDrawer for desktop/tablet layouts.

    Display modes:
    - Collapsed (expanded=False): Icon above label (vertical), 96px wide
    - Expanded (expanded=True): Icon + label (horizontal), 220px wide

    Both modes show labels. The active indicator (selection background) wraps:
    - Collapsed: Only the icon (56×32dp)
    - Expanded: Both icon and label

    Users can toggle between modes with optional menu button.

    For type-safe index, use IntEnum:
        class Section(IntEnum):
            HOME = 0
            SEARCH = 1
        NavigationRail(children=[...], index=Section.HOME)
    """

    def __init__(
        self,
        children: Sequence[RailItem],
        index: Union[int, _ObservableValue[int]] = 0,
        on_select: Optional[Callable[[int], None]] = None,
        expanded: Union[bool, _ObservableValue[bool]] = False,
        show_menu_button: bool = True,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ) -> None:
        # Store expanded state before calling super().__init__
        # so _calculate_width() works correctly
        self._is_expanded = expanded.value if isinstance(expanded, _ObservableValue) else bool(expanded)

        # If width is not specified, use calculated width
        if width is None:
            # Calculate default width based on expanded state
            default_width = 220 if self._is_expanded else 96
            width = default_width

        super().__init__(width=width, height=height, padding=padding)

        self._item_buttons: list[_RailItemButton] = []

        self._rail_items: Sequence[RailItem] = list(children)
        self.on_select = on_select
        self.show_menu_button = show_menu_button

        # Handle index (Observable or plain int)
        self._index_observable: Optional[_ObservableValue[int]] = None
        self._index_subscription = None
        if isinstance(index, _ObservableValue):
            self._index_observable = index
            self._current_index = self._validate_index(index.value)
            self._index_subscription = index.subscribe(self._on_index_changed)
        else:
            self._current_index = self._validate_index(int(index))

        # Handle expanded (Observable or plain bool)
        self._expanded_observable: Optional[_ObservableValue[bool]] = None
        self._expanded_subscription = None
        if isinstance(expanded, _ObservableValue):
            self._expanded_observable = expanded
            # _is_expanded already set above
            self._expanded_subscription = expanded.subscribe(self._on_expanded_changed)
        # else: _is_expanded already set above

        # Ensure subscriptions are released when this widget is removed from the tree.
        self.on_dispose(self.dispose)

        # Build UI
        self._rebuild_ui()

    def _on_index_changed(self, new_index: int) -> None:
        """Handle Observable index changes."""
        old_index = self._current_index
        self._current_index = self._validate_index(new_index)
        if old_index != self._current_index:
            self._update_selected(old_index, self._current_index)

    def _update_selected(self, old_index: int, new_index: int) -> None:
        if not self._item_buttons:
            self._rebuild_ui()
            return
        if 0 <= old_index < len(self._item_buttons):
            self._item_buttons[old_index].set_selected(False)
        if 0 <= new_index < len(self._item_buttons):
            self._item_buttons[new_index].set_selected(True)
        self.invalidate()

    def _on_expanded_changed(self, new_expanded: bool) -> None:
        """Handle Observable expanded changes."""
        old_expanded = self._is_expanded
        self._is_expanded = bool(new_expanded)
        if old_expanded != self._is_expanded:
            # Update width based on new expanded state
            new_width = 220 if self._is_expanded else 96
            self._width_sizing = Sizing.fixed(new_width)
            self._rebuild_ui()
            self.mark_needs_layout()

    def _validate_index(self, index: int) -> int:
        """Ensure index is within valid range."""
        if not self._rail_items:
            return 0
        return max(0, min(index, len(self._rail_items) - 1))

    def _rebuild_ui(self) -> None:
        """Rebuild the navigation rail UI."""
        # Clear existing children
        self.clear_children()

        # Calculate width based on expanded state
        rail_width = self._calculate_width()

        # Build menu button if enabled
        menu_button = None
        if self.show_menu_button:
            menu_button = self._build_menu_button()
            if self._is_expanded:
                # Align with item icon center in expanded mode.
                menu_button = Box(child=menu_button, padding=(8, 0, 0, 0))

        # Build rail items
        item_buttons = []
        for idx, rail_item in enumerate(self._rail_items):
            selected = idx == self._current_index

            def _on_click(i: int = idx) -> None:
                self._handle_item_click(i)

            button = _RailItemButton(
                rail_item=rail_item,
                selected=selected,
                expanded=self._is_expanded,
                on_click=_on_click,
            )
            item_buttons.append(button)
        self._item_buttons = item_buttons

        # Build column layout
        children = []
        if menu_button is not None:
            children.append(menu_button)
        children.extend(item_buttons)

        # Expanded: start-aligned; Collapsed: centered in the 96dp rail.
        cross_alignment = "start" if self._is_expanded else "center"
        rail_column = Column(
            children=children,
            gap=0 if self._is_expanded else 4,
            padding=(12, 44, 12, 12),
            cross_alignment=cross_alignment,
            width=Sizing.fixed(rail_width),
            height=Sizing.flex(1),
        )

        # Add background
        rail_bg = Box(
            child=rail_column,
            background_color=ColorRole.SURFACE,
            width=Sizing.fixed(rail_width),
            height=Sizing.flex(1),
        )

        self.add_child(rail_bg)

    def _calculate_width(self) -> int:
        """Calculate rail width based on expanded state."""
        if self.width_sizing.kind == "fixed":
            # Use explicit width if provided
            return int(self.width_sizing.value)
        # M3 defaults: 96dp collapsed, 220dp expanded
        return 220 if self._is_expanded else 96

    def _build_menu_button(self) -> Widget:
        """Build the menu toggle button."""
        icon_name = "menu" if not self._is_expanded else "menu_open"
        from nuiitivet.material.styles.icon_style import IconStyle

        icon = Icon(icon_name, size=24, style=IconStyle(color=ColorRole.ON_SURFACE))

        # Wrap with InteractionHostMixin for click handling
        class MenuButton(InteractionHostMixin, Box):
            def __init__(self, child: Widget, on_click: Callable[[], None]):
                super().__init__(
                    child=child,
                    width=Sizing.fixed(56),
                    height=Sizing.fixed(56),
                    alignment="center",
                )
                self._state = InteractionState(disabled=False)
                self.enable_hover()
                self.enable_click(on_click=on_click)

        return MenuButton(icon, self._toggle_expanded)

    def _toggle_expanded(self) -> None:
        """Toggle expanded state."""
        if self._expanded_observable is not None:
            # Update Observable
            self._expanded_observable.value = not self._is_expanded
        else:
            # Update local state
            self._is_expanded = not self._is_expanded
            # Update width based on new expanded state
            new_width = 220 if self._is_expanded else 96
            self._width_sizing = Sizing.fixed(new_width)
            self._rebuild_ui()
            self.mark_needs_layout()

    def _handle_item_click(self, index: int) -> None:
        """Handle item selection."""
        if self._index_observable is not None:
            # Update Observable
            self._index_observable.value = index
        else:
            # Update local state
            old_index = self._current_index
            self._current_index = index
            if old_index != self._current_index:
                self._update_selected(old_index, self._current_index)

        # Fire callback
        if self.on_select is not None:
            self.on_select(index)

    @property
    def current_index(self) -> int:
        """Get the currently selected item index."""
        return self._current_index

    @property
    def is_expanded(self) -> bool:
        """Get the current expanded state."""
        return self._is_expanded

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Calculate preferred size for the navigation rail."""
        rail_width = self._calculate_width()

        # Get height from child if present
        children = self.children_snapshot()
        if children:
            child = children[0]
            child_w, child_height = child.preferred_size(max_width=rail_width, max_height=max_height)
            preferred_w = max(int(rail_width), int(child_w))
            preferred_h = int(child_height)

            if max_width is not None:
                preferred_w = min(int(preferred_w), int(max_width))
            if max_height is not None:
                preferred_h = min(int(preferred_h), int(max_height))

            return (int(preferred_w), int(preferred_h))

        # Default minimum height
        preferred_w = int(rail_width)
        preferred_h = 400
        if max_width is not None:
            preferred_w = min(int(preferred_w), int(max_width))
        if max_height is not None:
            preferred_h = min(int(preferred_h), int(max_height))
        return (int(preferred_w), int(preferred_h))

    def layout(self, width: int, height: int) -> None:
        """Layout the navigation rail and its child."""
        super().layout(width, height)

        children = self.children_snapshot()
        if not children:
            return

        # Layout the single child (Box containing Column)
        child = children[0]
        rail_width = self._calculate_width()
        child.layout(rail_width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint the NavigationRail."""
        children = self.children_snapshot()
        if not children:
            return

        # Auto-layout fallback
        if any(c.layout_rect is None for c in children):
            self.layout(width, height)

        # Paint the child
        child = children[0]
        rect = child.layout_rect
        if rect is None:
            return

        rel_x, rel_y, w, h = rect
        abs_x = x + rel_x
        abs_y = y + rel_y

        child.set_last_rect(abs_x, abs_y, w, h)
        child.paint(canvas, abs_x, abs_y, w, h)

    def dispose(self) -> None:
        """Clean up subscriptions."""
        if self._index_subscription is not None:
            self._index_subscription.dispose()
            self._index_subscription = None
        if self._expanded_subscription is not None:
            self._expanded_subscription.dispose()
            self._expanded_subscription = None
