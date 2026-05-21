"""Material App - Basic Usage."""

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
                    Text("Hello, Material Design!"),
                    Button("Get Started", style=ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    app = App(
        content=HomeScreen(),
        title_bar=nv.DefaultTitleBar(title="Material App"),
        width=400,
        height=240,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
