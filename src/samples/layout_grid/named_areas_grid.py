"""Named areas grid sample."""

from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def _card(label: str, width="100%", height="100%") -> md.FilledCard:
    return md.FilledCard(
        md.Text(label),
        padding=12,
        alignment="center",
        width=width,
        height=height,
    )


def main(png: str = ""):
    widget = nv.Grid.named_areas(
        rows=[60, "100%", "auto"],
        columns=["auto", "100%"],
        areas=[
            ["header", "header"],
            ["sidebar", "content"],
            ["sidebar", "footer"],
        ],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[
            nv.GridItem.named_area("header", _card("Header")),
            # Sidebar: width is auto (content based)
            nv.GridItem.named_area("sidebar", _card("Sidebar", width=None)),
            nv.GridItem.named_area("content", _card("Main content")),
            # Footer: height is auto (content based)
            nv.GridItem.named_area("footer", _card("Footer", height=None)),
        ],
    )

    app = md.MaterialApp(
        content=widget, title_bar=nv.DefaultTitleBar(title="nv.Grid Layout (Named Areas)"), width=400, height=400
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
