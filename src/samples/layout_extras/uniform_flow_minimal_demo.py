import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    tiles = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

    widget = nv.UniformFlow(
        columns=3,
        main_gap=8,
        cross_gap=8,
        padding=12,
        aspect_ratio=1.0,
        children=[
            md.FilledCard(md.Text(t), alignment="center", padding=12) for t in tiles
        ],
        width=320,
    )

    root = nv.Container(alignment="center", child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="nv.UniformFlow Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
