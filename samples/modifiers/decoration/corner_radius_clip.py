import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Radius"),
                alignment="center",
            ).modifier(nv.background("#2196F3") | nv.corner_radius(16)),
            nv.Container(
                width=100,
                height=100,
                child=nv.Text("Clip"),
                alignment="center",
            ).modifier(nv.background("#FF9800") | nv.clip()),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(content=content, title="Corner Radius & Clip", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
