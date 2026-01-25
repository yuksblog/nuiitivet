import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    # 親の枠（150x150）
    widget = md.OutlinedCard(
        width=150,
        height=150,
        padding=10,
        # 子が大きい（200x200）-> そのままはみ出して表示される
        child=md.FilledCard(
            width=200,
            height=200,
            child=md.Text("Overflow Content"),
        ),
    )

    # Center it so we can see the overflow clearly
    root = nv.Container(padding=100, child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="Default Overflow"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
