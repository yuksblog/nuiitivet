import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, border


def main(png: str = ""):
    content = nv.Row(
        children=[
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Background"),
                alignment="center",
            ).modifier(background("#E0E0E0")),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Border"),
                alignment="center",
            ).modifier(border(color="#F44336", width=4)),
            nv.Container(
                width=100,
                height=100,
                child=md.Text("Both"),
                alignment="center",
            ).modifier(background("#E0E0E0") | border(color="#4CAF50", width=2)),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Background & Border"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
