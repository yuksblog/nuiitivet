import nuiitivet.material as nv


def _cell(label: str) -> nv.Card:
    return nv.Card(
        nv.Text(label),
        padding=12,
        alignment="center",
        width="wt",
        height="wt",
    )


def main(png: str = ""):
    # 2行 x 2列 のレイアウト
    widget = nv.Grid(
        # 列の定義: 左側は自動、右側は残り全部
        columns=["auto", "wt"],
        # 行の定義: 上は 60px、下は残り全部
        rows=[60, "wt"],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[
            # 左上 (row=0, column=0)
            nv.GridItem(_cell("Menu"), row=0, column=0),
            # 右上 (row=0, column=1)
            nv.GridItem(_cell("Header"), row=0, column=1),
            # 下の段すべて (row=1, column=0〜1)
            # 複数セルにまたがる場合はリストで範囲を指定
            nv.GridItem(_cell("Main Content"), row=1, column=[0, 1]),
        ],
    )

    app = nv.App(nv.Window(content=widget, title="Basic nv.Grid"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
