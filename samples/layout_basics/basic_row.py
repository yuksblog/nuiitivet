import nuiitivet.material as nv


def main(png: str = ""):
    actions = nv.Row(
        children=[
            nv.Button("Back", style=nv.ButtonStyle.outlined()),
            nv.Button("Next", style=nv.ButtonStyle.filled()),
        ],
        gap=12,
        padding=16,
    )

    app = nv.App(content=actions, title="Basic nv.Row", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
