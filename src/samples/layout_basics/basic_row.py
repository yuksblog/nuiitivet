import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    actions = nv.Row(
        children=[
            md.OutlinedButton("Back"),
            md.FilledButton("Next"),
        ],
        gap=12,
        padding=16,
    )

    app = md.MaterialApp(content=actions, title_bar=nv.DefaultTitleBar(title="Basic nv.Row"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
