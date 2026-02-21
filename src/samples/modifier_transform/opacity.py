import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, opacity


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=md.Text("100%"),
                alignment="center",
            ).modifier(background("#F44336")),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("50%"),
                alignment="center",
            ).modifier(background("#F44336") | opacity(0.5)),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("20%"),
                alignment="center",
            ).modifier(background("#F44336") | opacity(0.2)),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Opacity Modifier"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
