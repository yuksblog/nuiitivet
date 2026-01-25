"""Deck + NavigationRail integration sample - typical desktop app layout."""

from enum import IntEnum

from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.material.text_fields import OutlinedTextField
from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.deck import Deck
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.observable.value import _ObservableValue


class Section(IntEnum):
    """Type-safe section indices for navigation."""

    DASHBOARD = 0
    ANALYTICS = 1
    USERS = 2
    SETTINGS = 3


class DesktopAppDemo(ComposableWidget):
    """Demonstrate typical desktop application layout with NavigationRail + Deck."""

    def __init__(self):
        super().__init__()
        self.current_section = _ObservableValue(Section.DASHBOARD)
        self.rail_expanded = _ObservableValue(True)

        # State for each section (preserved when switching)
        self.dashboard_note = _ObservableValue("Dashboard notes...")
        self.analytics_filter = _ObservableValue("Last 7 days")
        self.users_search = _ObservableValue("")
        self.settings_name = _ObservableValue("App Name")

    def build(self) -> Widget:
        # Navigation rail (left side)
        rail = NavigationRail(
            children=[
                RailItem(icon="dashboard", label="Dashboard"),
                RailItem(icon="bar_chart", label="Analytics"),
                RailItem(icon="people", label="Users"),
                RailItem(icon="settings", label="Settings"),
            ],
            index=self.current_section,
            expanded=self.rail_expanded,
            show_menu_button=True,
            on_select=lambda idx: setattr(self.current_section, "value", idx),
        )

        # Content area - shows one section at a time
        content = Deck(
            children=[
                self._build_dashboard_section(),
                self._build_analytics_section(),
                self._build_users_section(),
                self._build_settings_section(),
            ],
            index=self.current_section,
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

        return Row(
            [rail, content],
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

    def _build_dashboard_section(self) -> Widget:
        """Dashboard section with preserved state."""
        return FilledCard(
            Column(
                [
                    Text("Dashboard"),
                    Text(""),
                    Text("Welcome to your dashboard!"),
                    Text("Enter notes below (state preserved when navigating):"),
                    OutlinedTextField(
                        value=self.dashboard_note,
                        label="Type dashboard notes...",
                        width=Sizing.fixed(400),
                    ),
                ],
                gap=12,
                padding=20,
                cross_alignment="start",
            ),
            style=CardStyle.filled().copy_with(border_radius=0),
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

    def _build_analytics_section(self) -> Widget:
        """Analytics section with preserved state."""
        return FilledCard(
            Column(
                [
                    Text("Analytics"),
                    Text(""),
                    Text("View and analyze your data"),
                    Text("Filter (state preserved):"),
                    OutlinedTextField(
                        value=self.analytics_filter,
                        label="Enter time range...",
                        width=Sizing.fixed(300),
                    ),
                ],
                gap=12,
                padding=20,
                cross_alignment="start",
            ),
            style=CardStyle.filled().copy_with(border_radius=0),
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

    def _build_users_section(self) -> Widget:
        """Users section with preserved state."""
        return FilledCard(
            Column(
                [
                    Text("Users"),
                    Text(""),
                    Text("Manage your users"),
                    Text("Search users (state preserved):"),
                    OutlinedTextField(
                        value=self.users_search,
                        label="Search by name...",
                        width=Sizing.fixed(300),
                    ),
                ],
                gap=12,
                padding=20,
                cross_alignment="start",
            ),
            style=CardStyle.filled().copy_with(border_radius=0),
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

    def _build_settings_section(self) -> Widget:
        """Settings section with preserved state."""
        return FilledCard(
            Column(
                [
                    Text("Settings"),
                    Text(""),
                    Text("Configure your application"),
                    Text("App name (state preserved):"),
                    OutlinedTextField(
                        value=self.settings_name,
                        label="Enter app name...",
                        width=Sizing.fixed(300),
                    ),
                    Text(""),
                    Text("Note: All section states are independently preserved."),
                    Text("Try typing in fields and navigating between sections."),
                ],
                gap=12,
                padding=20,
                cross_alignment="start",
            ),
            style=CardStyle.filled().copy_with(border_radius=0),
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )


if __name__ == "__main__":
    demo = DesktopAppDemo()
    app = MaterialApp(content=demo, width=800, height=768)
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("deck_with_rail_demo.png")
            print("Rendered deck_with_rail_demo.png")
        except Exception as e:
            print(f"Desktop app demo requires pyglet/skia: {e}")
