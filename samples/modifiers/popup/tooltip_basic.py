import nuiitivet.material as nv

target = nv.Container(
    width=160,
    height=40,
    child=nv.Text("Hover me"),
    alignment="center",
).modifier(nv.tooltip(nv.Tooltip("This is a tooltip"), delay=0.0))


def main(png: str = "") -> None:
    if png:
        # For screenshot: place Tooltip widget directly above anchor (overlay not captured by render_to_png)
        _anchor = nv.Container(width=160, height=40, child=nv.Text("Hover me"), alignment="center")
        app = nv.App(
            nv.Window(
                content=nv.Column(
                    children=[nv.Tooltip("This is a tooltip"), _anchor],
                    gap=4,
                    padding=24,
                    cross_alignment="start",
                ),
                title="tooltip Modifier",
                width=400,
            ),
        )
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    content = nv.Column(children=[nv.Container(height=20), target], gap=16, padding=24)
    app = nv.App(nv.Window(content=content, title="tooltip Modifier", width=400, height=200))
    app.run()


if __name__ == "__main__":
    main()
