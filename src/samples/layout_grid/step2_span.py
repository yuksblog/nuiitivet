"""Step 2 span sample."""

from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def _card(label: str) -> md.FilledCard:
    # Step 2: 単純なカード（サイズ指定なし）
    return md.FilledCard(
        md.Text(label),
        padding=12,
        alignment="center",
    )


def main(png: str = ""):
    # Header/Footer span 2 columns
    widget = nv.Grid(
        rows=["33%", "33%", "33%"],
        columns=["50%", "50%"],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[
            # Header: nv.Row 0, Col 0, Span 2 Cols
            nv.GridItem(_card("Header"), row=0, column=(0, 1)),
            # Sidebar: nv.Row 1-2, Col 0
            nv.GridItem(_card("Sidebar"), row=(1, 2), column=0),
            # Main: nv.Row 1, Col 1
            nv.GridItem(_card("Main"), row=1, column=1),
            # Footer: nv.Row 2, Col 1
            nv.GridItem(_card("Footer"), row=2, column=1),
        ],
    )

    app = md.MaterialApp(
        content=widget,
        title_bar=nv.DefaultTitleBar(title="Step 2: Spanning"),
        width=400,
        height=400,
    )
    if png:
        app.render_to_png(png)
        return
    app.run()


if __name__ == "__main__":
    main()
