import nuiitivet as nv
import nuiitivet.material as md


def _cell(label: str) -> md.FilledCard:
    return md.FilledCard(
        md.Text(label),
        padding=12,
        alignment="center",
        width="100%",
        height="100%",
    )


def main(png: str = ""):
    # 2行 x 2列 のレイアウト
    widget = nv.Grid(
        # 列の定義: 左側は自動、右側は残り全部
        columns=["auto", "100%"],
        # 行の定義: 上は 60px、下は残り全部
        rows=[60, "100%"],
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

    app = md.MaterialApp(content=widget, title_bar=nv.DefaultTitleBar(title="Basic nv.Grid"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
