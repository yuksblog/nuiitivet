import nuiitivet as nv
import nuiitivet.material as md


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
            md.Card(md.Text(tag, padding=8), style=md.CardStyle.outlined()) for tag in tags
        ],
        width=320,  # Limit width to show wrapping
    )

    root = nv.Container(alignment="center", child=widget)

    app = md.App(content=root, title_bar=nv.DefaultTitleBar(title="nv.Flow Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
