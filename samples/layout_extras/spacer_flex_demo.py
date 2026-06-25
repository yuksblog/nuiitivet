import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    widget = nv.Row(
        padding=16,
        gap=16,
        width=500,
        children=[
            md.Button("Left 1", style=md.ButtonStyle.outlined()),
            md.Button("Left 2", style=md.ButtonStyle.outlined()),
            nv.Spacer(width="100%"),
            md.Button("Right", style=md.ButtonStyle.filled()),
        ],
    )

    app = md.App(content=widget, title="nv.Spacer Flex Demo")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
