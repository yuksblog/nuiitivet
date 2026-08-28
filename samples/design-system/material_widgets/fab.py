"""Material Widgets - Fab variants and sizes."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.Text("Color variants (size s)"),
                nv.Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        nv.Fab("add", style=nv.FabStyle.primary()),
                        nv.Fab("edit", style=nv.FabStyle.secondary()),
                        nv.Fab("share", style=nv.FabStyle.tertiary()),
                    ],
                ),
                nv.Text("Sizes (s / m / l)"),
                nv.Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        nv.Fab("add", style=nv.FabStyle.primary("s")),
                        nv.Fab("add", style=nv.FabStyle.primary("m")),
                        nv.Fab("add", style=nv.FabStyle.primary("l")),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(nv.Window(content=content, title="Fab", width=440, height=320))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
