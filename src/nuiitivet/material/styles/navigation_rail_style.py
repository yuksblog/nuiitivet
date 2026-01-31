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
    """

    background: Optional[ColorSpec] = ColorRole.SURFACE
    indicator_color: Optional[ColorSpec] = ColorRole.SECONDARY_CONTAINER
    selected_icon_color: Optional[ColorSpec] = ColorRole.ON_SECONDARY_CONTAINER
    icon_color: Optional[ColorSpec] = ColorRole.ON_SURFACE_VARIANT
    selected_label_color: Optional[ColorSpec] = ColorRole.ON_SURFACE
    label_color: Optional[ColorSpec] = ColorRole.ON_SURFACE_VARIANT
    label_text_style: Optional[TextStyle] = None
    menu_icon_color: Optional[ColorSpec] = ColorRole.ON_SURFACE

    def copy_with(self, **changes) -> "NavigationRailStyle":
        """Return a copy of this style with the given changes."""
        return replace(self, **changes)
