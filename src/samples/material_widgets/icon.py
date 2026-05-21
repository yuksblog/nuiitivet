"""Material Widgets - Icon (Material Symbols) showcase."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Icon, Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def _cell(name: str, size: int) -> Column:
    return Column(
        gap=4,
        cross_alignment="center",
        children=[Icon(name, size=size), Text(name)],
    )


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=20,
            cross_alignment="start",
            children=[
                Text("Sizes (24 / 32 / 40)"),
                Row(
                    gap=24,
                    children=[
                        Icon("favorite", size=24),
                        Icon("favorite", size=32),
                        Icon("favorite", size=40),
                    ],
                ),
                Text("Common symbols"),
                Row(
                    gap=24,
                    children=[
                        _cell("home", 32),
                        _cell("search", 32),
                        _cell("settings", 32),
                        _cell("person", 32),
                        _cell("notifications", 32),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="Icon"),
        width=560,
        height=280,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
