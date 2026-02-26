"""Test NavigationRail widget."""

from enum import IntEnum

import pytest

from nuiitivet.material.badge import BadgeValue, LargeBadge, SmallBadge
from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.widgets.interaction import FocusNode
from nuiitivet.observable.value import _ObservableValue


def test_navigation_rail_basic_creation():
    """NavigationRail should create with default settings."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
        RailItem(icon="person", label="Profile"),
    ]
    rail = NavigationRail(children=items)

    assert rail.current_index == 0
    assert not rail.is_expanded
    assert len(rail._rail_items) == 3


def test_navigation_rail_with_initial_index():
    """NavigationRail should accept initial index."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
        RailItem(icon="person", label="Profile"),
    ]
    rail = NavigationRail(children=items, index=1)

    assert rail.current_index == 1


def test_navigation_rail_expanded_mode():
    """NavigationRail should support expanded mode."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
    ]
    rail = NavigationRail(children=items, expanded=True)

    assert rail.is_expanded


def test_navigation_rail_with_observable_index():
    """NavigationRail should work with Observable index."""
    index_obs = _ObservableValue(0)
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
        RailItem(icon="person", label="Profile"),
    ]
    rail = NavigationRail(children=items, index=index_obs)

    assert rail.current_index == 0

    # Change index via observable
    index_obs.value = 2
    assert rail.current_index == 2


def test_navigation_rail_with_observable_expanded():
    """NavigationRail should work with Observable expanded."""
    expanded_obs = _ObservableValue(False)
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
    ]
    rail = NavigationRail(children=items, expanded=expanded_obs)

    assert not rail.is_expanded

    # Toggle expanded via observable
    expanded_obs.value = True
    assert rail.is_expanded


def test_navigation_rail_on_select_callback():
    """NavigationRail should fire on_select callback."""
    selected_index = []

    def on_select(idx: int):
        selected_index.append(idx)

    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
        RailItem(icon="person", label="Profile"),
    ]
    rail = NavigationRail(children=items, on_select=on_select)

    # Simulate item click
    rail._handle_item_click(1)

    assert len(selected_index) == 1
    assert selected_index[0] == 1
    assert rail.current_index == 1


def test_navigation_rail_index_validation():
    """NavigationRail should validate index bounds."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
    ]
    rail = NavigationRail(children=items, index=10)

    # Index should be clamped
    assert rail.current_index == 1  # Max valid index


def test_navigation_rail_custom_icon_widget():
    """NavigationRail should reject Widget instances in RailItem."""
    from nuiitivet.material.icon import Icon

    custom_icon = Icon("home", size=32)
    with pytest.raises(TypeError):
        RailItem(icon=custom_icon, label="Home")  # type: ignore[arg-type]


def test_navigation_rail_custom_label_widget():
    """NavigationRail should reject Widget instances in RailItem."""
    from nuiitivet.material.text import Text

    custom_label = Text("Custom Home")
    with pytest.raises(TypeError):
        RailItem(icon="home", label=custom_label)  # type: ignore[arg-type]


def test_navigation_rail_width_calculation():
    """NavigationRail should calculate width correctly."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
    ]

    rail_collapsed = NavigationRail(children=items, expanded=False)
    assert rail_collapsed._calculate_width() == 96

    rail_expanded = NavigationRail(children=items, expanded=True)
    assert rail_expanded._calculate_width() == 220


def test_navigation_rail_custom_width():
    """NavigationRail should respect custom width."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
    ]
    rail = NavigationRail(children=items, width=150)

    assert rail._calculate_width() == 150


def test_navigation_rail_no_menu_button():
    """NavigationRail should hide menu button when disabled."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
    ]
    rail = NavigationRail(children=items, show_menu_button=False)

    assert not rail.show_menu_button


def test_navigation_rail_with_int_enum():
    """NavigationRail should work with IntEnum index."""

    class Section(IntEnum):
        HOME = 0
        SEARCH = 1
        PROFILE = 2

    index_obs = _ObservableValue(Section.HOME)
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
        RailItem(icon="person", label="Profile"),
    ]
    rail = NavigationRail(children=items, index=index_obs)

    assert rail.current_index == 0

    index_obs.value = Section.PROFILE
    assert rail.current_index == 2


def test_navigation_rail_empty_children():
    """NavigationRail should handle empty children list."""
    rail = NavigationRail(children=[])

    assert rail.current_index == 0
    assert len(rail._rail_items) == 0


def test_navigation_rail_dispose_cleanup():
    """NavigationRail should clean up subscriptions on dispose."""
    index_obs = _ObservableValue(0)
    expanded_obs = _ObservableValue(False)
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="search", label="Search"),
    ]
    rail = NavigationRail(children=items, index=index_obs, expanded=expanded_obs)

    # Should have subscriptions
    assert rail._index_subscription is not None
    assert rail._expanded_subscription is not None

    # Dispose should clean up
    rail.dispose()
    assert rail._index_subscription is None
    assert rail._expanded_subscription is None


def test_navigation_rail_with_style():
    """NavigationRail should accept style parameter."""
    from nuiitivet.material.styles.navigation_rail_style import NavigationRailStyle
    from nuiitivet.material.theme.color_role import ColorRole
    from nuiitivet.widgets.box import Box

    style = NavigationRailStyle(
        background=ColorRole.PRIMARY,
        indicator_color=ColorRole.SECONDARY,
        selected_icon_color=ColorRole.ON_SECONDARY,
    )

    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, style=style)

    assert rail.style == style
    # Verify internal structure reflected the style (indirectly)
    # The first child should be a Box with background_color=ColorRole.PRIMARY
    assert len(rail.children) == 1
    box = rail.children[0]
    assert isinstance(box, Box)
    # Note: background_color usually stored as _background_color or similar, check Box implementation
    # or just trust the logic if prop check is hard.
    # Box typically exposes background_color as property or argument to constructor.
    assert box.bgcolor == ColorRole.PRIMARY


def test_rail_item_with_style():
    """RailItem should accept style parameter."""
    from nuiitivet.material.styles.navigation_rail_style import NavigationRailStyle
    from nuiitivet.material.theme.color_role import ColorRole

    style = NavigationRailStyle(
        icon_color=ColorRole.ERROR,
    )

    item = RailItem(icon="settings", label="Settings", style=style)
    assert item.style == style


def test_rail_item_interactive_inheritance():
    """Verify RailItem uses InteractiveWidget for MD3 visual effects."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items)

    # Force UI build
    if not rail._item_buttons:
        rail._rebuild_ui()

    button = rail._item_buttons[0]
    assert isinstance(button, InteractiveWidget)


def test_rail_item_no_focus():
    """Verify RailItem does not accept keyboard focus (MD3 spec)."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items)

    # Force UI build
    if not rail._item_buttons:
        rail._rebuild_ui()

    button = rail._item_buttons[0]
    # InteractiveWidget adds FocusNode by default, but NavigationRail should remove it
    assert button.get_node(FocusNode) is None


def test_rail_item_selection_state():
    """Verify state.selected updates."""
    items = [
        RailItem(icon="home", label="Home"),
        RailItem(icon="settings", label="Settings"),
    ]
    rail = NavigationRail(children=items, index=0)

    # Force UI build
    if not rail._item_buttons:
        rail._rebuild_ui()

    btn1 = rail._item_buttons[0]
    btn2 = rail._item_buttons[1]

    # Initial state
    assert btn1.state.selected is True
    assert btn2.state.selected is False

    # Change selection via internal handler (simulating click)
    rail._handle_item_click(1)

    assert btn1.state.selected is False
    assert btn2.state.selected is True


# ---------------------------------------------------------------------------
# Badge tests
# ---------------------------------------------------------------------------


def test_rail_item_badge_observable_is_none_by_default():
    """RailItem should have no badge observable by default."""
    item = RailItem(icon="home", label="Home")
    assert item.badge_observable is None


def test_rail_item_badge_observable_stored():
    """RailItem should store the provided badge observable."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.small())
    item = RailItem(icon="home", label="Home", badge=badge_obs)
    assert item.badge_observable is badge_obs


def test_rail_item_button_no_badge_when_not_provided():
    """_RailItemButton should have no badge widget when no observable given."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    assert button._badge_widget is None


def test_rail_item_button_small_badge_created():
    """_RailItemButton should create SmallBadge for BadgeValue.small()."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.small())
    items = [RailItem(icon="home", label="Home", badge=badge_obs)]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    assert isinstance(button._badge_widget, SmallBadge)


def test_rail_item_button_large_badge_created():
    """_RailItemButton should create LargeBadge for BadgeValue.large()."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.large(5))
    items = [RailItem(icon="home", label="Home", badge=badge_obs)]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    assert isinstance(button._badge_widget, LargeBadge)
    assert button._badge_widget.count == 5


def test_rail_item_button_none_badge_hides_widget():
    """_RailItemButton should clear badge widget when BadgeValue.none() is set."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.small())
    items = [RailItem(icon="home", label="Home", badge=badge_obs)]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    assert button._badge_widget is not None

    badge_obs.value = BadgeValue.none()
    assert button._badge_widget is None


def test_rail_item_badge_updates_from_small_to_large():
    """_RailItemButton should switch from SmallBadge to LargeBadge on value change."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.small())
    items = [RailItem(icon="home", label="Home", badge=badge_obs)]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    assert isinstance(button._badge_widget, SmallBadge)

    badge_obs.value = BadgeValue.large(42)
    assert isinstance(button._badge_widget, LargeBadge)
    assert button._badge_widget.count == 42


def test_rail_item_badge_layout_small():
    """Badge rect is computed using MD3 small badge stick offsets (top-right of icon)."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.small())
    items = [RailItem(icon="home", label="Home", badge=badge_obs)]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    button.layout(96, 72)

    assert button._badge_rect is not None
    _bx, _by, bw, bh = button._badge_rect
    # SmallBadge default is 6x6 per MD3 spec.
    assert bw > 0 and bh > 0


def test_rail_item_badge_layout_large():
    """Badge rect is computed using MD3 large badge stick offsets (top-right of icon)."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.large(3))
    items = [RailItem(icon="home", label="Home", badge=badge_obs)]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    button.layout(96, 72)

    assert button._badge_rect is not None
    _bx, _by, bw, bh = button._badge_rect
    assert bw > 0 and bh > 0


def test_rail_item_badge_subscription_disposed():
    """Badge subscription should be cleaned up on button dispose."""
    badge_obs: _ObservableValue[BadgeValue] = _ObservableValue(BadgeValue.small())
    items = [RailItem(icon="home", label="Home", badge=badge_obs)]
    rail = NavigationRail(children=items)

    button = rail._item_buttons[0]
    assert button._badge_subscription is not None

    button._dispose_badge()
    assert button._badge_subscription is None
