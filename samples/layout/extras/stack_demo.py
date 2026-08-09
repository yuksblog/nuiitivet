import nuiitivet.material as nv


def main(png: str = ""):
    widget = nv.Stack(
        width=200,
        height=200,
        alignment="center",  # デフォルトの配置位置
        children=[
            # 1. 背景（奥）。Stack の子はそれぞれが軸の唯一の請求者なので、
            #    重なりを見せるには "wt" ではなく固定サイズを使う。
            nv.Card(
                nv.Text(""),
                width=200,
                height=200,
                style=nv.CardStyle(background="#BBDEFB"),
            ),
            nv.Card(
                nv.Text(""),
                width=150,
                height=150,
                style=nv.CardStyle(background="#90CAF9"),
            ),
            nv.Card(
                nv.Text("Overlay Text"),
                width=100,
                height=100,
                alignment="center",
                style=nv.CardStyle(background="#64B5F6"),
            ),
        ],
    )

    root = nv.Card(
        widget,
        alignment="center",
        style=nv.CardStyle(background=None, border_radius=0),
    )

    app = nv.App(content=root, title="nv.Stack Demo")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
