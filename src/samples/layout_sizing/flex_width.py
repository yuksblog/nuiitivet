import nuiitivet.material as md
import nuiitivet as nv


def main(png: str = ""):
    widget = md.FilledCard(
        width="100%",
        child=md.Text("Full Width Box"),
        padding=16,
        alignment="center",
    )

    app = md.MaterialApp(content=widget, title_bar=nv.DefaultTitleBar(title="Full Width Box"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
