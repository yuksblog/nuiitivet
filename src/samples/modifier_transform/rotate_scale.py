import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, rotate, scale


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Rotate 45°"),
                alignment="center",
            ).modifier(background("#4CAF50") | rotate(45)),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Scale 1.5x"),
                alignment="center",
            ).modifier(background("#2196F3") | scale(1.5)),
        ],
        gap=48,
        padding=48,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Rotate & Scale"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
