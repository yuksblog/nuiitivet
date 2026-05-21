"""Material Widgets - Fab variants and sizes."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Fab, FabStyle, Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                Text("Color variants (size s)"),
                Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        Fab("add", style=FabStyle.primary()),
                        Fab("edit", style=FabStyle.secondary()),
                        Fab("share", style=FabStyle.tertiary()),
                    ],
                ),
                Text("Sizes (s / m / l)"),
                Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        Fab("add", style=FabStyle.primary("s")),
                        Fab("add", style=FabStyle.primary("m")),
                        Fab("add", style=FabStyle.primary("l")),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="Fab"),
        width=440,
        height=320,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
