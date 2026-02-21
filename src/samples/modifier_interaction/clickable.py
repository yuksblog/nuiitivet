import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, clickable, corner_radius


def main(png: str = ""):
    content = nv.Column(
        children=[
            nv.Container(
                width=200,
                height=50,
                child=md.Text("Click Me!"),
                alignment="center",
            ).modifier(background("#4CAF50") | corner_radius(8) | clickable(on_click=lambda: print("Clicked!"))),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Clickable Modifier"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
