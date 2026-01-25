import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    content = nv.Column(
        children=[
            md.FilledButton("Button 1"),
            md.FilledButton("Button 2"),
            nv.Spacer(height=24),  # ここだけ広げる
            md.OutlinedButton("Button 3"),
            nv.Spacer(height=24),  # ここだけ広げる
            md.FilledButton("Button 4"),
        ],
        gap=12,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="nv.Spacer Demo"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
