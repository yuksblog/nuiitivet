"""Navigation Rail Style definition.

This module provides the `NavigationRailStyle` dataclass used by the
`NavigationRail` widget.
"""

from dataclasses import dataclass, replace
from typing import Optional

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec
from nuiitivet.material.styles.text_style import TextStyle

# Trailing margin (dp) kept between the expanded active-indicator pill and the
# rail's trailing edge when the indicator width is auto-derived. Chosen so the
# 220dp default reproduces the historical 174dp pill (220 - 20 leading - 26).
_EXPANDED_INDICATOR_TRAILING_MARGIN = 26.0


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
        container_width_expanded_min: Minimum expanded width (dp). Also the
            default expanded width when the ``NavigationRail`` ``width`` is not a
            fixed value. Matches the M3 lower bound (220dp).
        container_width_expanded_max: Maximum expanded width (dp). Fixed
            ``width`` values are clamped into
            ``[container_width_expanded_min, container_width_expanded_max]``.
            Matches the M3 upper bound (360dp); raise it to allow wider rails.
        icon_size: Icon size.
        item_height: Item height.
        indicator_height_collapsed: Indicator height when collapsed.
        indicator_width_collapsed: Indicator width when collapsed.
        indicator_width_expanded: Active-indicator (pill) width when expanded.
            ``None`` (default) auto-derives it from the resolved expanded width
            so the pill scales across the M3 expanded range (220-360dp), leaving
            a fixed trailing margin to the rail edge. Set an explicit value to
            pin it. See :meth:`expanded_indicator_width`.
        indicator_horizontal_padding: Horizontal padding inside indicator.
        label_height: Label height.
        horizontal_label_width: Label width in expanded mode. ``None`` (default)
            auto-derives it from the resolved indicator width so the label fills
            the pill minus symmetric ``indicator_horizontal_padding`` inner
            padding (and never overflows it) at any container width. Set an
            explicit value to pin it. See :meth:`expanded_label_width`.
        label_horizontal_inset: Horizontal inset applied to each side of the
            collapsed (vertical) label so it never touches the rail edges.
            The default 8dp yields an 80dp label box inside the 96dp rail,
            matching the M3 collapsed navigation rail container width (80dp).
        gap_collapsed: Gap between items when collapsed.
        gap_expanded: Gap between items when expanded.
        label_gap_expanded: Icon-label gap when expanded.
        menu_button_size: Menu button size (layout slot and hit target).
        menu_state_layer_size: Diameter of the menu button's state layer and
            focus ring, drawn centered in the button. The default 40dp is the
            standard icon button state layer; the surrounding
            ``menu_button_size`` stays the pointer target.
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
    container_width_expanded_min: float = 220.0
    container_width_expanded_max: float = 360.0
    icon_size: float = 24.0
    item_height: float = 56.0
    indicator_height_collapsed: float = 32.0
    indicator_width_collapsed: float = 56.0
    indicator_width_expanded: Optional[float] = None
    indicator_horizontal_padding: float = 16.0
    label_height: float = 20.0
    horizontal_label_width: Optional[float] = None
    label_horizontal_inset: float = 8.0
    gap_collapsed: float = 4.0
    gap_expanded: float = 0.0
    label_gap_expanded: float = 8.0
    menu_button_size: float = 56.0
    menu_state_layer_size: float = 40.0
    top_padding: float = 44.0

    def clamp_expanded_width(self, value: float) -> float:
        """Clamp an expanded width into the allowed MD3 range.

        Returns ``value`` bounded by
        ``[container_width_expanded_min, container_width_expanded_max]``.
        """
        lo = self.container_width_expanded_min
        hi = max(lo, self.container_width_expanded_max)
        return max(lo, min(hi, value))

    def expanded_indicator_width(self, expanded_width: float) -> float:
        """Return the resolved active-indicator width for *expanded_width*.

        If :attr:`indicator_width_expanded` is set, it is returned as-is.
        Otherwise the pill scales with *expanded_width*, keeping the leading
        margin ``(container_width_collapsed - indicator_width_collapsed) / 2``
        and a fixed trailing margin to the rail edge.
        """
        if self.indicator_width_expanded is not None:
            return self.indicator_width_expanded
        leading_margin = max(
            0.0,
            (self.container_width_collapsed - self.indicator_width_collapsed) / 2.0,
        )
        return max(
            0.0,
            expanded_width - leading_margin - _EXPANDED_INDICATOR_TRAILING_MARGIN,
        )

    def expanded_label_width(self, expanded_width: float) -> float:
        """Return the resolved horizontal label width for *expanded_width*.

        If :attr:`horizontal_label_width` is set, it is returned as-is.
        Otherwise the label fills the resolved indicator pill minus the icon,
        the icon-label gap, and a symmetric :attr:`indicator_horizontal_padding`
        inner padding on each side, so it never overflows the pill.
        """
        if self.horizontal_label_width is not None:
            return self.horizontal_label_width
        return max(
            0.0,
            self.expanded_indicator_width(expanded_width)
            - 2.0 * self.indicator_horizontal_padding
            - self.icon_size
            - self.label_gap_expanded,
        )

    def copy_with(self, **changes) -> "NavigationRailStyle":
        """Return a copy of this style with the given changes."""
        return replace(self, **changes)
