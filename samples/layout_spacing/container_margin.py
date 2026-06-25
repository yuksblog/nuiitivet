import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    content = nv.Column(
        children=[
            md.Button("Button 1", style=md.ButtonStyle.filled()),
            md.Button("Button 2", style=md.ButtonStyle.filled()),
            nv.Container(
                child=md.Button("Button 3", style=md.ButtonStyle.outlined()),
                padding=24,  # この要素だけ周囲に24px確保
            ),
            md.Button("Button 4", style=md.ButtonStyle.filled()),
        ],
        gap=12,
        padding=16,
    )

    app = md.App(content=content, title="nv.Container Margin", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
