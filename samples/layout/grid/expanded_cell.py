import nuiitivet.material as nv


def build_root() -> nv.Widget:
    widget = nv.Grid(
        rows=[200],
        columns=[200],
        children=[
            nv.GridItem(
                child=nv.Card(
                    # カードをセルのサイズいっぱいに広げる
                    width="wt",
                    height="wt",
                    alignment="center",
                    child=nv.Text("Expanded md.Card"),
                ),
                row=0,
                column=0,
            )
        ],
    )

    root = nv.Container(padding=50, child=widget)
    return root


def main(png: str = ""):
    # Just a simple 1x1 grid to show expansion

    app = nv.App(nv.Window(content=build_root, title="Expanded Cell"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
