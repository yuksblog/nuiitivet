"""Material Theme - No Theme (default).

Demonstrates the default appearance when no theme is passed to App.
MaterialApp defaults to MaterialTheme.light("#6750A4").
"""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Button, Text
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class HomeScreen(ComposableWidget):
    def build(self) -> Widget:
        return Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Column(
                gap=16,
                children=[
                    Text("Material App"),
                    Button("Get Started", style=ButtonStyle.filled()),
                    Button("Learn More", style=ButtonStyle.outlined()),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    app = App(
        content=HomeScreen(),
        title_bar=nv.DefaultTitleBar(title="No Theme"),
        width=400,
        height=280,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
