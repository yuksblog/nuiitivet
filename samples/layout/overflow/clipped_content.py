import nuiitivet.material as nv


def main(png: str = ""):
    widget = nv.Card(
        width=150,
        height=150,
        padding=10,
        child=nv.Card(
            width=200,
            height=200,
            child=nv.Text("Clipped Content"),
        ),
        style=nv.CardStyle.outlined(),
    ).modifier(
        nv.clip()
    )  # 枠からはみ出た部分は描画されない

    root = nv.Container(padding=100, child=widget)

    app = nv.App(nv.Window(content=root, title="Clipped Content", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
