import nuiitivet as nv

from nuiitivet.material import FilledButton, MaterialApp, Text
from nuiitivet.layout.column import Column
from nuiitivet.navigation import Navigator
from nuiitivet.widgeting.widget import ComposableWidget
from nuiitivet.widgets.box import Box


class DetailsScreen(ComposableWidget):
    def build(self):
        def go_back() -> None:
            Navigator.root().pop()

        return Box(
            background_color="#F5F7FF",
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            child=Column(
                padding=16,
                gap=12,
                children=[
                    Text("Details Screen"),
                    FilledButton("Back", on_click=go_back),
                ],
            ),
        )


class HomeScreen(ComposableWidget):
    def build(self):
        def navigate_to_details() -> None:
            Navigator.root().push(DetailsScreen())

        return Column(
            padding=16,
            gap=12,
            children=[
                Text("Home Screen"),
                FilledButton("Go to Details", on_click=navigate_to_details),
            ],
        )


def main(png_path: str | None = None) -> None:
    app = MaterialApp(
        content=HomeScreen(),
        title_bar=nv.DefaultTitleBar(title="Navigation Basic"),
        width=400,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
