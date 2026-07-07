"""Material Widgets - DockedToolbar / HorizontalFloatingToolbar."""

from __future__ import annotations

import nuiitivet.material as nv


def _actions() -> list[nv.IconButton]:
    return [
        nv.IconButton("menu", style=nv.IconButtonStyle.standard()),
        nv.IconButton("search", style=nv.IconButtonStyle.standard()),
        nv.IconButton("favorite", style=nv.IconButtonStyle.filled()),
        nv.IconButton("more_vert", style=nv.IconButtonStyle.outlined()),
    ]


def main(png_path: str = "") -> None:
    docked = nv.DockedToolbar(_actions(), style=nv.ToolbarStyle.standard())
    docked.width_sizing = 480

    floating = nv.HorizontalFloatingToolbar(
        _actions(),
        padding=(12, 8, 12, 8),
        style=nv.ToolbarStyle.standard(),
    )

    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.Text("DockedToolbar"),
                docked,
                nv.Text("FloatingToolbar"),
                floating,
            ],
        ),
    )
    app = nv.App(
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
