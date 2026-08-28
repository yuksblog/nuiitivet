"""Material Widgets - Icon (Material Symbols) showcase."""

from __future__ import annotations

import nuiitivet.material as nv


def _cell(name: str, size: int) -> nv.Column:
    return nv.Column(
        gap=4,
        cross_alignment="center",
        children=[nv.Icon(name, size=size), nv.Text(name)],
    )


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=20,
            cross_alignment="start",
            children=[
                nv.Text("Sizes (24 / 32 / 40)"),
                nv.Row(
                    gap=24,
                    children=[
                        nv.Icon("favorite", size=24),
                        nv.Icon("favorite", size=32),
                        nv.Icon("favorite", size=40),
                    ],
                ),
                nv.Text("Common symbols"),
                nv.Row(
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
    app = nv.App(nv.Window(content=content, title="Icon", width=560, height=280))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
