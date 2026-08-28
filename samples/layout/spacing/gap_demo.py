import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Column(
        children=[
            nv.Button("Button 1", style=nv.ButtonStyle.filled()),
            nv.Button("Button 2", style=nv.ButtonStyle.filled()),
            nv.Button("Button 3", style=nv.ButtonStyle.outlined()),
            nv.Button("Button 4", style=nv.ButtonStyle.filled()),
        ],
        gap=12,
        padding=16,
    )

    app = nv.App(nv.Window(content=content, title="Gap Demo", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
