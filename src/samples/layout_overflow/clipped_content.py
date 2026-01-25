import nuiitivet as nv
import nuiitivet.material as md
import nuiitivet.modifiers as mod


def main(png: str = ""):
    widget = md.OutlinedCard(
        width=150,
        height=150,
        padding=10,
        child=md.FilledCard(
            width=200,
            height=200,
            child=md.Text("Clipped Content"),
        ),
    ).modifier(
        mod.clip()
    )  # 枠からはみ出た部分は描画されない

    root = nv.Container(padding=100, child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="Clipped Content"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
