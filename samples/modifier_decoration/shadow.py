import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Shadow"),
                alignment="center",
            ).modifier(nv.background("#FFFFFF") | nv.shadow(color="#000000", blur=8, offset=(0, 4))),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("With Radius"),
                alignment="center",
            ).modifier(
                nv.background("#FFFFFF") | nv.corner_radius(16) | nv.shadow(color="#000000", blur=12, offset=(0, 6))
            ),
        ],
        gap=32,
        padding=32,
    )

    app = nv.App(content=content, title="Shadow Modifier", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
