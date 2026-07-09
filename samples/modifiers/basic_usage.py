import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Column(
        children=[
            nv.Text("Hello").modifier(nv.background("#FF5722")),
            nv.Text("Rounded Box").modifier(nv.background("#2196F3") | nv.corner_radius(8)),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(content=content, title="Modifier Basic Usage", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
