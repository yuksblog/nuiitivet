"""Material Theme - Multiple Themes.

Demonstrates switching between multiple named themes using ThemeRegistryIntent
and ThemeModeIntent. Themes are registered on mount and switched by string key.
"""

from __future__ import annotations

import nuiitivet.material as nv

ocean_light, ocean_dark = nv.ThemeFactory.from_seed_pair("#00639B")
forest_light, forest_dark = nv.ThemeFactory.from_seed_pair("#386A20")


class HomeScreen(nv.ComposableWidget):
    def build(self) -> nv.Widget:
        def switch(name: str):
            return lambda: nv.App.of(self).dispatch(nv.ThemeModeIntent(theme=name))

        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=12,
                children=[
                    nv.Text("Multiple Themes"),
                    nv.Button("Ocean Light", style=nv.ButtonStyle.filled(), on_click=switch("ocean-light")),
                    nv.Button("Ocean Dark", style=nv.ButtonStyle.tonal(), on_click=switch("ocean-dark")),
                    nv.Button("Forest Light", style=nv.ButtonStyle.filled(), on_click=switch("forest-light")),
                    nv.Button("Forest Dark", style=nv.ButtonStyle.tonal(), on_click=switch("forest-dark")),
                ],
            ),
        )


def main() -> None:
    app = nv.App(
        content=HomeScreen(),
        title="Multiple Themes",
        theme=ocean_light,
        width=400,
        height=340,
    )
    app.dispatch(
        nv.ThemeRegistryIntent(
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
