"""Layout tests for NavigationRail widget."""

from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.material.theme.color_role import ColorRole


def test_navigation_rail_layout_common_metrics():
    """Test common layout metrics for NavigationRail."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items)
    rail.layout(800, 600)

    # Check common item properties
    item_button = rail._item_buttons[0]
    indicator = item_button._indicator_box

    # "Nav rail item active indicator shape md.sys.shape.corner.full"
    # Corner radius should be half of height (16 for 32dp height).
    assert indicator.corner_radius == 16

    # "Nav rail collapsed container color md.sys.color.surface"
    rail_bg = rail.children[0]
    # Box uses .bgcolor property
    assert rail_bg.bgcolor == ColorRole.SURFACE

    # "Nav rail collapsed container shape md.sys.shape.corner.none"
    assert rail_bg.corner_radius == 0
    assert rail_bg.shadow_blur == 0  # Elevation 0


def test_navigation_rail_layout_collapsed():
    """Test layout metrics specifically for Collapsed state."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=False)
    rail.layout(800, 600)

    # "Nav rail collapsed container width 96dp"
    assert rail._calculate_width() == 96

    item_button = rail._item_buttons[0]
    indicator = item_button._indicator_box

    # "Nav rail item vertical active indicator height 32dp"
    assert indicator.height_sizing.value == 32
    assert indicator.height_sizing.kind == "fixed"

    # "Nav rail item vertical label text font size 12pt"
    # Vertical label is used in collapsed mode
    label = item_button._vertical_label
    assert label.style.font_size == 12

    # "Nav rail item vertical icon label space 4dp"
    # In code: self._content_column.gap = 4.0 * (1.0 - t)
    content_col = item_button._content_column
    assert content_col.gap == 4

    # "Nav rail item vertical leading-space 16dp" check internal padding
    l, t, r, b = indicator.padding
    assert l == 16
    assert r == 16


def test_navigation_rail_layout_expanded():
    """Test layout metrics specifically for Expanded state."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=True)
    rail.layout(800, 600)

    # "Nav rail expanded container width minimum 220dp"
    assert rail._calculate_width() == 220

    # "Nav rail expanded container elevation 0"
    rail_bg = rail.children[0]
    assert rail_bg.shadow_blur == 0

    item_button = rail._item_buttons[0]

    # "Nav rail item horizontal label text font size 14pt"
    h_label = item_button._horizontal_label
    assert h_label.style.font_size == 14

    # "Nav rail item horizontal active indicator height 56dp"
    indicator = item_button._indicator_box
    assert indicator.height_sizing.value == 56

    # "Nav rail item horizontal icon-label-space 8dp"
    gap_spacer = item_button._icon_gap_spacer
    assert gap_spacer.width_sizing.value == 8

    # "Nav rail item horizontal full width leading space 16dp"
    ind_l, ind_t, ind_r, ind_b = indicator.padding
    assert ind_l == 16
    assert ind_r == 16
