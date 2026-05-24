"""Material Theme - Dark Mode.

Demonstrates dark mode using the same seed color as the light theme.
"""

from __future__ import annotations

from nuiitivet.material import App, Button, Text, ThemeFactory
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
        title="Dark Mode",
        theme=ThemeFactory.dark("#00639B"),
        width=400,
        height=280,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
