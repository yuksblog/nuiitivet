import nuiitivet.material as nv


class NestedDetails(nv.ComposableWidget):
    def build(self):
        def go_back() -> None:
            nv.Navigator.of(self).pop()

        return nv.Box(
            background_color="#F5F7FF",
            width="wt",
            height="wt",
            child=nv.Column(
                padding=16,
                gap=12,
                children=[
                    nv.Text("Nested Details"),
                    nv.Button("Back (Nested)", on_click=go_back, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


class NestedHome(nv.ComposableWidget):
    def build(self):
        def go_deeper() -> None:
            nv.Navigator.of(self).push(NestedDetails())

        return nv.Column(
            padding=16,
            gap=12,
            children=[
                nv.Text("Nested Home"),
                nv.Button("Go Deeper (Nested)", on_click=go_deeper, style=nv.ButtonStyle.filled()),
            ],
        )


class FullScreenDetails(nv.ComposableWidget):
    def build(self):
        def go_back() -> None:
            nv.Navigator.root().pop()

        return nv.Box(
            background_color="#EEF7F0",
            width="wt",
            height="wt",
            child=nv.Column(
                padding=20,
                gap=12,
                children=[
                    nv.Text("Full Screen Details"),
                    nv.Button("Back (Full Screen)", on_click=go_back, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


class MainScreen(nv.ComposableWidget):
    def build(self):
        def open_full_screen() -> None:
            nv.Navigator.root().push(FullScreenDetails())

        return nv.Row(
            width="wt",
            height="wt",
            gap=12,
            padding=12,
            children=[
                nv.Container(
                    width=200,
                    height="wt",
                    child=nv.Column(
                        padding=16,
                        gap=12,
                        children=[
                            nv.Text("Sidebar Menu"),
                            nv.Button("Open Full Screen", on_click=open_full_screen, style=nv.ButtonStyle.filled()),
                        ],
                    ),
                ),
                nv.Container(
                    width="wt",
                    height="wt",
                    child=nv.Navigator(NestedHome()),
                ),
            ],
        )


def main(png_path: str | None = None) -> None:
    app = nv.App(
        content=MainScreen(),
        title="Nested Navigation",
        width=400,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
