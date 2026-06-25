import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    content = nv.Column(
        children=[
            md.Button("Button 1", style=md.ButtonStyle.filled()),
            md.Button("Button 2", style=md.ButtonStyle.filled()),
            md.Button("Button 3", style=md.ButtonStyle.outlined()),  # これだけスタイル違い
            md.Button("Button 4", style=md.ButtonStyle.filled()),
        ],
        padding=16,
    )

    app = md.App(content=content, title="Padding Demo", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
