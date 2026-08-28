import nuiitivet.material as nv


def main(png: str = ""):
    tags = [
        "Python",
        "UI",
        "Flow",
        "Wrap",
        "Widgets",
        "Layout",
        "Material",
        "Desktop",
    ]

    widget = nv.Flow(
        main_gap=8,
        cross_gap=8,
        padding=12,
        children=[
            nv.Card(nv.Text(tag, padding=8), style=nv.CardStyle.outlined()) for tag in tags
        ],
        width=320,  # Limit width to show wrapping
    )

    root = nv.Container(alignment="center", child=widget)

    app = nv.App(nv.Window(content=root, title="nv.Flow Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
