"""Navigation Rail Style definition.

This module provides the `NavigationRailStyle` dataclass used by the
`NavigationRail` widget.
"""

from dataclasses import dataclass, replace
from typing import Optional

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec
from nuiitivet.material.styles.text_style import TextStyle


@dataclass(frozen=True)
class NavigationRailStyle:
    """Immutable style for NavigationRail widgets.

    Attributes:
        background: The background color of the rail.
        indicator_color: The color of the active indicator.
        selected_icon_color: The color of the icon when selected.
        icon_color: The color of the icon when unselected.
        selected_label_color: The color of the label when selected.
        label_color: The color of the label when unselected.
        label_text_style: The base text style for labels.
        menu_icon_color: The color of the menu icon.
        container_width_collapsed: Width when collapsed.
        container_width_expanded: Width when expanded.
        icon_size: Icon size.
        item_height: Item height.
        indicator_height_collapsed: Indicator height when collapsed.
        indicator_width_collapsed: Indicator width when collapsed.
        indicator_width_expanded: Indicator width when expanded.
        indicator_horizontal_padding: Horizontal padding inside indicator.
        label_height: Label height.
        horizontal_label_width: Label width in expanded mode.
        gap_collapsed: Gap between items when collapsed.
        gap_expanded: Gap between items when expanded.
        label_gap_expanded: Icon-label gap when expanded.
        menu_button_size: Menu button size.
        top_padding: Top padding before first item.
    """

    background: Optional[ColorSpec] = ColorRole.SURFACE
    indicator_color: Optional[ColorSpec] = ColorRole.SECONDARY_CONTAINER
    selected_icon_color: Optional[ColorSpec] = ColorRole.ON_SECONDARY_CONTAINER
    icon_color: Optional[ColorSpec] = ColorRole.ON_SURFACE_VARIANT
    selected_label_color: Optional[ColorSpec] = ColorRole.ON_SURFACE
    label_color: Optional[ColorSpec] = ColorRole.ON_SURFACE_VARIANT
    label_text_style: Optional[TextStyle] = None
    menu_icon_color: Optional[ColorSpec] = ColorRole.ON_SURFACE
    container_width_collapsed: float = 96.0
    container_width_expanded: float = 220.0
    icon_size: float = 24.0
    item_height: float = 56.0
    indicator_height_collapsed: float = 32.0
    indicator_width_collapsed: float = 56.0
    indicator_width_expanded: float = 174.0
    indicator_horizontal_padding: float = 16.0
    label_height: float = 20.0
    horizontal_label_width: float = 110.0
    gap_collapsed: float = 4.0
    gap_expanded: float = 0.0
    label_gap_expanded: float = 8.0
    menu_button_size: float = 56.0
    top_padding: float = 44.0

    def copy_with(self, **changes) -> "NavigationRailStyle":
        """Return a copy of this style with the given changes."""
        return replace(self, **changes)
