import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Rotate 45°"),
                alignment="center",
            ).modifier(nv.background("#4CAF50") | nv.rotate(45)),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Scale 1.5x"),
                alignment="center",
            ).modifier(nv.background("#2196F3") | nv.scale(1.5)),
        ],
        gap=48,
        padding=48,
    )

    app = nv.App(content=content, title="Rotate & Scale", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
