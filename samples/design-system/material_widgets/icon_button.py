"""Material Widgets - IconButton and IconToggleButton variants."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=12,
            cross_alignment="start",
            children=[
                nv.Text("IconButton"),
                nv.Row(
                    gap=12,
                    children=[
                        nv.IconButton("home", style=nv.IconButtonStyle.standard()),
                        nv.IconButton("favorite", style=nv.IconButtonStyle.filled()),
                        nv.IconButton("search", style=nv.IconButtonStyle.outlined()),
                        nv.IconButton("settings", style=nv.IconButtonStyle.tonal()),
                        nv.IconButton("add", style=nv.IconButtonStyle.filled(), disabled=True),
                    ],
                ),
                nv.Text("IconToggleButton"),
                nv.Row(
                    gap=12,
                    children=[
                        nv.IconToggleButton("home", selected=False, style=nv.IconToggleButtonStyle.standard()),
                        nv.IconToggleButton("favorite", selected=True, style=nv.IconToggleButtonStyle.filled()),
                        nv.IconToggleButton("search", selected=False, style=nv.IconToggleButtonStyle.outlined()),
                        nv.IconToggleButton("settings", selected=True, style=nv.IconToggleButtonStyle.tonal()),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(
        content=content,
        title="IconButton",
        width=520,
        height=260,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
