"""Test NavigationRail widget."""

from enum import IntEnum

import pytest

from nuiitivet.material.navigation_rail import NavigationRail, RailItem
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
