import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    actions = nv.Row(
        children=[
            md.Button("Back", style=md.ButtonStyle.outlined()),
            md.Button("Next", style=md.ButtonStyle.filled()),
        ],
        gap=12,
        padding=16,
    )

    app = md.App(content=actions, title="Basic nv.Row", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
