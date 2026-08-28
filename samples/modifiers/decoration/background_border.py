import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Background"),
                alignment="center",
            ).modifier(nv.background("#E0E0E0")),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Border"),
                alignment="center",
            ).modifier(nv.border(color="#F44336", width=4)),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Both"),
                alignment="center",
            ).modifier(nv.background("#E0E0E0") | nv.border(color="#4CAF50", width=2)),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(nv.Window(content=content, title="Background & Border", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
