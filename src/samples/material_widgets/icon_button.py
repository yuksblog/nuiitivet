"""Material Widgets - IconButton and IconToggleButton variants."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, IconButton, IconToggleButton, Text
from nuiitivet.material.styles import IconButtonStyle, IconToggleButtonStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=12,
            cross_alignment="start",
            children=[
                Text("IconButton"),
                Row(
                    gap=12,
                    children=[
                        IconButton("home", style=IconButtonStyle.standard()),
                        IconButton("favorite", style=IconButtonStyle.filled()),
                        IconButton("search", style=IconButtonStyle.outlined()),
                        IconButton("settings", style=IconButtonStyle.tonal()),
                        IconButton("add", style=IconButtonStyle.filled(), disabled=True),
                    ],
                ),
                Text("IconToggleButton"),
                Row(
                    gap=12,
                    children=[
                        IconToggleButton("home", selected=False, style=IconToggleButtonStyle.standard()),
                        IconToggleButton("favorite", selected=True, style=IconToggleButtonStyle.filled()),
                        IconToggleButton("search", selected=False, style=IconToggleButtonStyle.outlined()),
                        IconToggleButton("settings", selected=True, style=IconToggleButtonStyle.tonal()),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="IconButton"),
        width=520,
        height=260,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
