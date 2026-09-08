import nuiitivet.material as nv


def build_root() -> nv.Widget:
    widget = nv.Card(
        width="wt",
        child=nv.Text("Full Width Box"),
        padding=16,
        alignment="center",
    )
    return widget


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="Full Width Box", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
