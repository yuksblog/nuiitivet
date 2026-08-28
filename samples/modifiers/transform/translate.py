import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Normal"),
                alignment="center",
            ).modifier(nv.background("#FF9800")),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Translated"),
                alignment="center",
            ).modifier(nv.background("#FF9800") | nv.translate((20, 20))),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(nv.Window(content=content, title="Translate Modifier", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
