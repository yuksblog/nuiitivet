import nuiitivet.material as nv


def build_root() -> nv.Widget:
    widget = nv.Card(
        width=200,  # 幅を 200px に固定
        height=100,  # 高さを 100px に固定
        child=nv.Text("Fixed Size Box"),
        padding=16,
        alignment="center",
    )

    # Wrap in center container for better visibility
    root = nv.Container(alignment="center", child=widget)
    return root


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="Fixed Size", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
