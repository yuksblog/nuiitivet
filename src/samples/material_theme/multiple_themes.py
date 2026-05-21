"""Material Theme - Multiple Themes.

Demonstrates switching between multiple named themes using ThemeRegistryIntent
and ThemeModeIntent. Themes are registered on mount and switched by string key.
"""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Button, Text, ThemeFactory
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.theme.intents import ThemeRegistryIntent, ThemeModeIntent
from nuiitivet.widgeting.widget import ComposableWidget, Widget

ocean_light, ocean_dark = ThemeFactory.from_seed_pair("#00639B")
forest_light, forest_dark = ThemeFactory.from_seed_pair("#386A20")


class HomeScreen(ComposableWidget):
    def build(self) -> Widget:
        def switch(name: str):
            return lambda: App.of(self).dispatch(ThemeModeIntent(theme=name))

        return Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Column(
                gap=12,
                children=[
                    Text("Multiple Themes"),
                    Button("Ocean Light", style=ButtonStyle.filled(), on_click=switch("ocean-light")),
                    Button("Ocean Dark", style=ButtonStyle.tonal(), on_click=switch("ocean-dark")),
                    Button("Forest Light", style=ButtonStyle.filled(), on_click=switch("forest-light")),
                    Button("Forest Dark", style=ButtonStyle.tonal(), on_click=switch("forest-dark")),
                ],
            ),
        )


def main() -> None:
    app = App(
        content=HomeScreen(),
        title_bar=nv.DefaultTitleBar(title="Multiple Themes"),
        theme=ocean_light,
        width=400,
        height=340,
    )
    app.dispatch(
        ThemeRegistryIntent(
            themes={
                "ocean-light": ocean_light,
                "ocean-dark": ocean_dark,
                "forest-light": forest_light,
                "forest-dark": forest_dark,
            }
        )
    )
    app.run()


if __name__ == "__main__":
    main()
