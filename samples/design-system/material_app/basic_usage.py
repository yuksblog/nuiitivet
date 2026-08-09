"""Material App - Basic Usage."""

import nuiitivet.material as nv


class HomeScreen(nv.ComposableWidget):
    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Hello, Material Design!"),
                    nv.Button("Get Started", style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    app = nv.App(
        content=HomeScreen(),
        title="Material App",
        width=400,
        height=240,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
