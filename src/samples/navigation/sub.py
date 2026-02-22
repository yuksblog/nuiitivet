import nuiitivet as nv

from nuiitivet.material import FilledButton, MaterialApp, Text
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.navigation import Navigator, PageRoute
from nuiitivet.widgeting.widget import ComposableWidget
from nuiitivet.widgets.box import Box


class NestedDetails(ComposableWidget):
    def build(self):
        def go_back() -> None:
            Navigator.of(self).pop()

        return Box(
            background_color="#F5F7FF",
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            child=Column(
                padding=16,
                gap=12,
                children=[
                    Text("Nested Details"),
                    FilledButton("Back (Nested)", on_click=go_back),
                ],
            ),
        )


class NestedHome(ComposableWidget):
    def build(self):
        def go_deeper() -> None:
            Navigator.of(self).push(NestedDetails())

        return Column(
            padding=16,
            gap=12,
            children=[
                Text("Nested Home"),
                FilledButton("Go Deeper (Nested)", on_click=go_deeper),
            ],
        )


class FullScreenDetails(ComposableWidget):
    def build(self):
        def go_back() -> None:
            Navigator.root().pop()

        return Box(
            background_color="#EEF7F0",
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            child=Column(
                padding=20,
                gap=12,
                children=[
                    Text("Full Screen Details"),
                    FilledButton("Back (Full Screen)", on_click=go_back),
                ],
            ),
        )


class MainScreen(ComposableWidget):
    def build(self):
        def open_full_screen() -> None:
            Navigator.root().push(FullScreenDetails())

        return Row(
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            gap=12,
            padding=12,
            children=[
                Container(
                    width=200,
                    height=nv.Sizing.flex(1),
                    child=Column(
                        padding=16,
                        gap=12,
                        children=[
                            Text("Sidebar Menu"),
                            FilledButton("Open Full Screen", on_click=open_full_screen),
                        ],
                    ),
                ),
                Container(
                    width=nv.Sizing.flex(1),
                    height=nv.Sizing.flex(1),
                    child=MaterialNavigator(
                        routes=[
                            PageRoute(builder=lambda: NestedHome()),
                        ]
                    ),
                ),
            ],
        )


def main(png_path: str | None = None) -> None:
    app = MaterialApp(
        content=MainScreen(),
        title_bar=nv.DefaultTitleBar(title="Nested Navigation"),
        width=400,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
