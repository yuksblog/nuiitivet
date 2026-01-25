import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    content = nv.Column(
        children=[
            md.FilledButton("Button 1"),
            md.FilledButton("Button 2"),
            md.OutlinedButton("Button 3"),
            md.FilledButton("Button 4"),
        ],
        gap=12,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Gap Demo"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
