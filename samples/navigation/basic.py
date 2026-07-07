import nuiitivet.material as nv


class DetailsScreen(nv.ComposableWidget):
    def build(self):
        def go_back() -> None:
            nv.Navigator.root().pop()

        return nv.Box(
            background_color="#F5F7FF",
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            child=nv.Column(
                padding=16,
                gap=12,
                children=[
                    nv.Text("Details Screen"),
                    nv.Button("Back", on_click=go_back, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


class HomeScreen(nv.ComposableWidget):
    def build(self):
        def navigate_to_details() -> None:
            nv.Navigator.root().push(DetailsScreen())

        return nv.Column(
            padding=16,
            gap=12,
            children=[
                nv.Text("Home Screen"),
                nv.Button("Go to Details", on_click=navigate_to_details, style=nv.ButtonStyle.filled()),
            ],
        )


def main(png_path: str | None = None) -> None:
    app = nv.App(
        content=HomeScreen(),
        title="Navigation Basic",
        width=400,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
