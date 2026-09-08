import nuiitivet.material as nv


def build_root() -> nv.Widget:
    actions = nv.Row(
        children=[
            nv.Button("Back", style=nv.ButtonStyle.outlined()),
            nv.Button("Next", style=nv.ButtonStyle.filled()),
        ],
        gap=12,
        padding=16,
    )
    return actions


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="Basic nv.Row", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
