import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Column(
        children=[
            nv.Button("Button 1", style=nv.ButtonStyle.filled()),
            nv.Button("Button 2", style=nv.ButtonStyle.filled()),
            nv.Container(
                child=nv.Button("Button 3", style=nv.ButtonStyle.outlined()),
                padding=24,  # この要素だけ周囲に24px確保
            ),
            nv.Button("Button 4", style=nv.ButtonStyle.filled()),
        ],
        gap=12,
        padding=16,
    )

    app = nv.App(nv.Window(content=content, title="nv.Container Margin", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
