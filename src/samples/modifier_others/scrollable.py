import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, scrollable


def main(png: str = ""):
    items = [
        nv.Container(
            width=200,
            height=50,
            child=md.Text(f"Item {i}"),
            alignment="center",
        ).modifier(background("#E0E0E0"))
        for i in range(10)
    ]

    content = nv.Container(
        width=250,
        height=200,
        child=nv.Column(children=items, gap=8),
    ).modifier(scrollable(axis="y"))

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Scrollable Modifier"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
