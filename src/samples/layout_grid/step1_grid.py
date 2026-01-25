"""Step 1 grid sample."""

from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def _card(label: str) -> md.FilledCard:
    # Step 1: 単純なカード（サイズ指定なし）
    return md.FilledCard(
        md.Text(label),
        padding=12,
        alignment="center",
    )


def main(png: str = ""):
    # 3行 x 2列
    # Step 1: 単純に並べる (3Rows, 2Cols)
    widget = nv.Grid(
        rows=["33%", "33%", "33%"],
        columns=["50%", "50%"],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[
            # [0, 0] 左上
            nv.GridItem(_card("Header"), row=0, column=0),
            # [0, 1] 右上
            nv.GridItem(_card("(Empty)"), row=0, column=1),
            # [1, 0] Middle Left
            nv.GridItem(_card("Sidebar"), row=1, column=0),
            # [1, 1] Middle Right
            nv.GridItem(_card("Main"), row=1, column=1),
            # [2, 0] Bottom Left
            nv.GridItem(_card("(Empty)"), row=2, column=0),
            # [2, 1] Bottom Right
            nv.GridItem(_card("Footer"), row=2, column=1),
        ],
    )

    app = md.MaterialApp(
        content=widget,
        title_bar=nv.DefaultTitleBar(title="Step 1: Simple nv.Grid"),
        width=400,
        height=400,
    )
    if png:
        app.render_to_png(png)
        return
    app.run()


if __name__ == "__main__":
    main()
