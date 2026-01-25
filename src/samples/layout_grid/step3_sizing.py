"""Step 3 sizing sample."""

from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def _card(label: str) -> md.FilledCard:
    # サイズ指定なし
    return md.FilledCard(
        md.Text(label),
        padding=12,
        alignment="center",
    )


def main(png: str = ""):
    # Step 3: 行と列のサイズ定義を変更
    widget = nv.Grid(
        rows=[60, "100%", "auto"],
        columns=["auto", "100%"],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[
            # Header
            nv.GridItem(_card("Header"), row=0, column=(0, 1)),
            # Sidebar: "auto" 列に入る。縦結合で下に伸びる。
            nv.GridItem(_card("Sidebar"), row=(1, 2), column=0),
            # Main
            nv.GridItem(_card("Main"), row=1, column=1),
            # Footer: "auto" 行に入る。
            nv.GridItem(_card("Footer"), row=2, column=1),
        ],
    )

    app = md.MaterialApp(
        content=widget, title_bar=nv.DefaultTitleBar(title="Step 3: nv.Sizing Strategies"), width=400, height=400
    )
    if png:
        app.render_to_png(png)
        return
    app.run()


if __name__ == "__main__":
    main()
