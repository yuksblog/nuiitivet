import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, translate


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Normal"),
                alignment="center",
            ).modifier(background("#FF9800")),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Translated"),
                alignment="center",
            ).modifier(background("#FF9800") | translate((20, 20))),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Translate Modifier"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
