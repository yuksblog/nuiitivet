import nuiitivet.material as nv


def main(png: str = ""):
    widget = nv.Card(
        width="wt",
        child=nv.Text("Full Width Box"),
        padding=16,
        alignment="center",
    )

    app = nv.App(nv.Window(content=widget, title="Full Width Box", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
