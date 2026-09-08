import nuiitivet.material as nv


def build_root() -> nv.Widget:
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("100%"),
                alignment="center",
            ).modifier(nv.background("#F44336")),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("50%"),
                alignment="center",
            ).modifier(nv.background("#F44336") | nv.opacity(0.5)),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("20%"),
                alignment="center",
            ).modifier(nv.background("#F44336") | nv.opacity(0.2)),
        ],
        gap=16,
        padding=16,
    )
    return content


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="Opacity Modifier", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
