"""NavigationRail sample demonstrating basic usage and mode toggling."""

from enum import IntEnum

from nuiitivet.material.app import MaterialApp
from nuiitivet.material import BadgeValue, FilledButton, OutlinedButton, Text, TextButton
from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.observable.value import _ObservableValue


class Section(IntEnum):
    """Type-safe section indices."""

    HOME = 0
    SEARCH = 1
    LIBRARY = 2
    SETTINGS = 3


class NavigationRailDemo(ComposableWidget):
    """Demonstrate NavigationRail widget with mode toggling."""

    def __init__(self):
        super().__init__()
        self.selected_section = _ObservableValue(Section.HOME)
        self.rail_expanded = _ObservableValue(False)
        self.home_badge = _ObservableValue(BadgeValue.small())
        self.search_badge = _ObservableValue(BadgeValue.large(3))
        self.library_badge = _ObservableValue(BadgeValue.large(1))
        self.library_count = 1

    def _increment_library_badge(self) -> None:
        self.library_count += 1
        self.library_badge.value = BadgeValue.large(self.library_count)

    def _clear_library_badge(self) -> None:
        self.library_count = 0
        self.library_badge.value = BadgeValue.none()

    def _toggle_home_badge(self) -> None:
        if self.home_badge.value.kind == "none":
            self.home_badge.value = BadgeValue.small()
            return
        self.home_badge.value = BadgeValue.none()

    def _toggle_search_badge(self) -> None:
        if self.search_badge.value.kind == "none":
            self.search_badge.value = BadgeValue.large(3)
            return
        self.search_badge.value = BadgeValue.none()

    def build(self) -> Widget:
        section_label = self.selected_section.map(lambda idx: f"Section: {Section(int(idx)).name}")
        library_badge_label = self.library_badge.map(
            lambda b: "Library badge: none" if b.kind == "none" else f"Library badge: {b.kind}"
        )

        # Navigation rail
        rail = NavigationRail(
            children=[
                RailItem(icon="home", label="Home", badge=self.home_badge),
                RailItem(icon="search", label="Search Results", badge=self.search_badge),
                RailItem(icon="library_books", label="Library Collection", badge=self.library_badge),
                RailItem(icon="settings", label="Settings"),
            ],
            index=self.selected_section,
            expanded=self.rail_expanded,
            show_menu_button=True,
            on_select=lambda idx: setattr(self.selected_section, "value", idx),
            height=Sizing.flex(1),
        )

        # Content area - shows which section is selected
        content = FilledCard(
            Column(
                [
                    Text(section_label),
                    Text(""),
                    Text("Click the menu button to toggle rail mode"),
                    Text("Click items to navigate"),
                    Text(""),
                    Text("Badge Observable controls:"),
                    Text(library_badge_label),
                    Row(
                        [
                            FilledButton("Library +1", on_click=self._increment_library_badge),
                            OutlinedButton("Library clear", on_click=self._clear_library_badge),
                        ],
                        gap=8,
                    ),
                    Row(
                        [
                            TextButton("Toggle Home dot", on_click=self._toggle_home_badge),
                            TextButton("Toggle Search count", on_click=self._toggle_search_badge),
                        ],
                        gap=8,
                    ),
                ],
                gap=8,
                padding=20,
                cross_alignment="start",
            ),
            style=CardStyle.filled().copy_with(border_radius=0),
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

        return Row(
            [rail, content],
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )


if __name__ == "__main__":
    demo = NavigationRailDemo()
    app = MaterialApp(content=demo, width=800, height=600)
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("navigation_rail_demo.png")
            print("Rendered navigation_rail_demo.png")
        except Exception as e:
            print(f"NavigationRail demo requires pyglet/skia: {e}")
