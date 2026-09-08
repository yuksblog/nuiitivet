import nuiitivet.material as nv


def build_root() -> nv.Widget:
    widget = nv.Container(
        nv.Button("Centered Content", style=nv.ButtonStyle.filled()),
        width=250,
        height=200,
        alignment="center",
        padding=16,
    )
    return widget


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="nv.Container Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
