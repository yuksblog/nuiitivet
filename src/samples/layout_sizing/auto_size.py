import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    widget = md.FilledCard(
        # width/height 指定なし -> auto
        width="auto",
        height="auto",
        child=md.Text("This box fits the content"),
        padding=16,
        alignment="center",
    )

    root = nv.Container(alignment="center", child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="Auto Size"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
