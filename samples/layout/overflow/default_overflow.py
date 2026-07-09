import nuiitivet.material as nv


def main(png: str = ""):
    # 親の枠（150x150）
    widget = nv.Card(
        width=150,
        height=150,
        padding=10,
        # 子が大きい（200x200）-> そのままはみ出して表示される
        child=nv.Card(
            width=200,
            height=200,
            child=nv.Text("Overflow Content"),
        ),
        style=nv.CardStyle.outlined(),
    )

    # Center it so we can see the overflow clearly
    root = nv.Container(padding=100, child=widget)

    app = nv.App(content=root, title="Default Overflow", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
