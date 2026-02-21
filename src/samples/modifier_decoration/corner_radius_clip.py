import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, corner_radius, clip


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Radius"),
                alignment="center",
            ).modifier(background("#2196F3") | corner_radius(16)),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Clip"),
                alignment="center",
            ).modifier(background("#FF9800") | clip()),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Corner Radius & Clip"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
