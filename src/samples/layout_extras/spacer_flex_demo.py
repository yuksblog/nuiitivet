import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    widget = nv.Row(
        padding=16,
        gap=16,
        width=500,
        children=[
            md.OutlinedButton("Left 1"),
            md.OutlinedButton("Left 2"),
            nv.Spacer(width="100%"),
            md.FilledButton("Right"),
        ],
    )

    app = md.MaterialApp(content=widget, title_bar=nv.DefaultTitleBar(title="nv.Spacer Flex Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
