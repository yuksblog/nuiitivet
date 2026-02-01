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
            md.OutlinedCard(md.Text(tag, padding=(10, 6, 10, 6))) for tag in tags
        ],
        width=320,  # Limit width to show wrapping
    )

    root = nv.Container(alignment="center", child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="Flow (Wrap)"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
