"""NavigationRail sample demonstrating basic usage and mode toggling."""

from enum import IntEnum
from typing import Optional

from nuiitivet.material import App
from nuiitivet.material import Text, Button
from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.card import Card
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.material import ButtonStyle


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
        self.home_small_badge = _ObservableValue(True)
        self.search_large_badge: _ObservableValue[Optional[str]] = _ObservableValue("3")
        self.library_large_badge: _ObservableValue[Optional[str]] = _ObservableValue("1")
        self.library_count = 1

    def _increment_library_badge(self) -> None:
        self.library_count += 1
        self.library_large_badge.value = str(self.library_count)

    def _clear_library_badge(self) -> None:
        self.library_count = 0
        self.library_large_badge.value = None

    def _toggle_home_badge(self) -> None:
        self.home_small_badge.value = not self.home_small_badge.value

    def _toggle_search_badge(self) -> None:
        self.search_large_badge.value = None if self.search_large_badge.value else "3"

    def build(self) -> Widget:
        section_label = self.selected_section.map(lambda idx: f"Section: {Section(int(idx)).name}")
        library_badge_label = self.library_large_badge.map(
            lambda b: "Library badge: none" if not b else f"Library badge: {b}"
        )

        # Navigation rail
        rail = NavigationRail(
            children=[
                RailItem(icon="home", label="Home", small_badge=self.home_small_badge),
                RailItem(icon="search", label="Search Results", large_badge=self.search_large_badge),
                RailItem(icon="library_books", label="Library Collection", large_badge=self.library_large_badge),
                RailItem(icon="settings", label="Settings"),
            ],
            index=self.selected_section,
            expanded=self.rail_expanded,
            show_menu_button=True,
            on_select=lambda idx: setattr(self.selected_section, "value", idx),
            height=Sizing.flex(1),
        )

        # Content area - shows which section is selected
        content = Card(
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
                            Button("Library +1", on_click=self._increment_library_badge, style=ButtonStyle.filled()),
                            Button("Library clear", on_click=self._clear_library_badge, style=ButtonStyle.outlined()),
                        ],
                        gap=8,
                    ),
                    Row(
                        [
                            Button("Toggle Home dot", on_click=self._toggle_home_badge, style=ButtonStyle.text()),
                            Button("Toggle Search count", on_click=self._toggle_search_badge, style=ButtonStyle.text()),
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
    app = App(content=demo, width=800, height=600)
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("navigation_rail_demo.png")
            print("Rendered navigation_rail_demo.png")
        except Exception as e:
            print(f"NavigationRail demo requires pyglet/skia: {e}")
