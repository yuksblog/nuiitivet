"""Material Widgets - DockedToolbar / FloatingToolbar."""

from __future__ import annotations

from nuiitivet.material import App, DockedToolbar, FloatingToolbar, IconButton, Text
from nuiitivet.material.styles import IconButtonStyle, ToolbarStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container


def _actions() -> list[IconButton]:
    return [
        IconButton("menu", style=IconButtonStyle.standard()),
        IconButton("search", style=IconButtonStyle.standard()),
        IconButton("favorite", style=IconButtonStyle.filled()),
        IconButton("more_vert", style=IconButtonStyle.outlined()),
    ]


def main(png_path: str = "") -> None:
    docked = DockedToolbar(_actions(), style=ToolbarStyle.standard())
    docked.width_sizing = 480

    floating = FloatingToolbar(
        _actions(),
        padding=(12, 8, 12, 8),
        style=ToolbarStyle.standard(),
    )

    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                Text("DockedToolbar"),
                docked,
                Text("FloatingToolbar"),
                floating,
            ],
        ),
    )
    app = App(
        content=content,
        title="Toolbar",
        width=560,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
