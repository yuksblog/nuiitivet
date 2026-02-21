import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, corner_radius


def main(png: str = ""):
    content = nv.Column(
        children=[
            md.Text("Hello").modifier(background("#FF5722")),
            md.Text("Rounded Box").modifier(background("#2196F3") | corner_radius(8)),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Modifier Basic Usage"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
