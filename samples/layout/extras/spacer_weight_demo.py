import nuiitivet.material as nv


def build_root() -> nv.Widget:
    widget = nv.Row(
        padding=16,
        gap=16,
        width=500,
        children=[
            nv.Button("Left 1", style=nv.ButtonStyle.outlined()),
            nv.Button("Left 2", style=nv.ButtonStyle.outlined()),
            nv.Spacer(width="wt"),
            nv.Button("Right", style=nv.ButtonStyle.filled()),
        ],
    )
    return widget


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="nv.Spacer Flex Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
