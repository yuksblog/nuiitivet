"""Deck sample demonstrating tab switching and state preservation."""

from enum import IntEnum

from nuiitivet.material import App
from nuiitivet.material import Text
from nuiitivet.material.text_fields import TextField
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.deck import Deck
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.card import Card
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.material.buttons import Button
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.material import ButtonStyle
from nuiitivet.material.styles.text_field_style import TextFieldStyle


class ViewMode(IntEnum):
    """Type-safe view mode indices."""

    HOME = 0
    PROFILE = 1
    SETTINGS = 2


class DeckDemo(ComposableWidget):
    """Demonstrate Deck widget with tab switching."""

    def __init__(self):
        super().__init__()
        self.current_tab = _ObservableValue(ViewMode.HOME)

        # State for each tab (preserved when switching)
        self.home_text = _ObservableValue("Type in home...")
        self.profile_text = _ObservableValue("Type in profile...")
        self.settings_text = _ObservableValue("Type in settings...")

    def build(self) -> Widget:
        # Tab buttons
        tab_buttons = Row(
            [
                Button(
                    "Home",
                    on_click=lambda: setattr(self.current_tab, "value", ViewMode.HOME),
                    style=ButtonStyle.filled()),
                Button(
                    "Profile",
                    on_click=lambda: setattr(self.current_tab, "value", ViewMode.PROFILE),
                    style=ButtonStyle.filled()),
                Button(
                    "Settings",
                    on_click=lambda: setattr(self.current_tab, "value", ViewMode.SETTINGS),
                    style=ButtonStyle.filled()),
            ],
            gap=8,
            padding=12,
        )

        # Tab content (state is preserved when switching tabs)
        tab_content = Deck(
            children=[
                self._build_home_tab(),
                self._build_profile_tab(),
                self._build_settings_tab(),
            ],
            index=self.current_tab,
            padding=12,
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

        return Column(
            [
                Card(
                    tab_buttons,
                    style=CardStyle.filled().copy_with(border_radius=0),
                ),
                Card(
                    tab_content,
                    style=CardStyle.filled().copy_with(border_radius=0),
                    width=Sizing.flex(1),
                    height=Sizing.flex(1),
                ),
            ],
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

    def _build_home_tab(self) -> Widget:
        """Home tab with text field (state preserved)."""
        return Column(
            [
                Text("Home Tab"),
                Text("Enter text below and switch tabs to see state preservation:"),
                TextField(
                    value=self.home_text,
                    label="Type something...",
                    width=Sizing.fixed(400),
                    style=TextFieldStyle.outlined(),
                ),
            ],
            gap=12,
            cross_alignment="start",
        )

    def _build_profile_tab(self) -> Widget:
        """Profile tab with text field (state preserved)."""
        return Column(
            [
                Text("Profile Tab"),
                Text("This tab has its own text field with preserved state:"),
                TextField(
                    value=self.profile_text,
                    label="Type something...",
                    width=Sizing.fixed(400),
                    style=TextFieldStyle.outlined(),
                ),
            ],
            gap=12,
            cross_alignment="start",
        )

    def _build_settings_tab(self) -> Widget:
        """Settings tab with text field (state preserved)."""
        return Column(
            [
                Text("Settings Tab"),
                Text("All tabs maintain their state independently:"),
                TextField(
                    value=self.settings_text,
                    label="Type something...",
                    width=Sizing.fixed(400),
                    style=TextFieldStyle.outlined(),
                ),
                Text("Note: Deck keeps all children mounted,"),
                Text("so their state (text, scroll position, etc.) is preserved."),
            ],
            gap=12,
            cross_alignment="start",
        )


if __name__ == "__main__":
    demo = DeckDemo()
    app = App(content=demo, width=600, height=400)
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("deck_demo.png")
            print("Rendered deck_demo.png")
        except Exception as e:
            print(f"Deck demo requires pyglet/skia: {e}")
