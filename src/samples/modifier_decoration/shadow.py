import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, shadow, corner_radius


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Shadow"),
                alignment="center",
            ).modifier(background("#FFFFFF") | shadow(color="#000000", blur=8, offset=(0, 4))),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("With Radius"),
                alignment="center",
            ).modifier(background("#FFFFFF") | corner_radius(16) | shadow(color="#000000", blur=12, offset=(0, 6))),
        ],
        gap=32,
        padding=32,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Shadow Modifier"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
