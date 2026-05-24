"""Window Chrome - Custom (app-drawn) decoration."""

import nuiitivet as nv
from nuiitivet.runtime.app import App
from nuiitivet.material import Text
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.modifiers import background

SKIP_WINDOW_FRAME = True


def main(png_path: str = "") -> None:
    header = Row(
        children=[
            Text("My App", style=TextStyle(color="#ffffff", font_size=14)),
        ],
        cross_alignment="center",
        width="100%",
        height=40,
        padding=(12, 0),
    ).modifier(background("#1a237e"))

    app = App(
        content=Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Text("Custom Chrome"),
        ),
        title="My App",
        chrome=nv.CustomChrome(
            header=header,
            corner_radius=8,
        ),
        width=400,
        height=240,
        background="#e3f2fd",
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
