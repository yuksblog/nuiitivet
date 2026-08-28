"""Named areas grid sample."""

from __future__ import annotations
import nuiitivet.material as nv


def _card(label: str, width="wt", height="wt") -> nv.Card:
    return nv.Card(
        nv.Text(label),
        padding=12,
        alignment="center",
        width=width,
        height=height,
    )


def main(png: str = ""):
    widget = nv.Grid.named_areas(
        rows=[60, "wt", "auto"],
        columns=["auto", "wt"],
        areas=[
            ["header", "header"],
            ["sidebar", "content"],
            ["sidebar", "footer"],
        ],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[
            nv.GridItem.named_area(_card("Header"), "header"),
            # Sidebar: width is auto (content based)
            nv.GridItem.named_area(_card("Sidebar", width=None), "sidebar"),
            nv.GridItem.named_area(_card("Main content"), "content"),
            # Footer: height is auto (content based)
            nv.GridItem.named_area(_card("Footer", height=None), "footer"),
        ],
    )

    app = nv.App(nv.Window(content=widget, title="nv.Grid Layout (Named Areas)", width=400, height=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
