import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    tags = [
        "Python",
        "UI",
        "Framework",
        "Layout",
        "nv.Grid",
        "Flex",
        "nv.Widget",
        "Nuiitivet",
        "Extra Tag",
        "Another Tag",
    ]

    widget = nv.Flow(
        main_gap=8,
        cross_gap=8,
        padding=8,
        children=[md.OutlinedCard(child=md.Text(tag, padding=8)) for tag in tags],
        width=300,  # Limit width to force wrapping
    )

    root = nv.Container(alignment="center", child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="nv.Flow Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
