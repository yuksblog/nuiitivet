import nuiitivet.material as nv


def main(png: str = ""):
    tiles = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

    widget = nv.UniformFlow(
        columns=3,
        main_gap=8,
        cross_gap=8,
        padding=12,
        aspect_ratio=1.0,
        children=[
            nv.Card(nv.Text(t), alignment="center", padding=12) for t in tiles
        ],
        width=320,
    )

    root = nv.Container(alignment="center", child=widget)

    app = nv.App(nv.Window(content=root, title="nv.UniformFlow Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
