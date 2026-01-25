import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    # Just a simple 1x1 grid to show expansion
    widget = nv.Grid(
        rows=[200],
        columns=[200],
        children=[
            nv.GridItem(
                child=md.FilledCard(
                    # カードをセルのサイズいっぱいに広げる
                    width="100%",
                    height="100%",
                    alignment="center",
                    child=md.Text("Expanded md.Card"),
                ),
                row=0,
                column=0,
            )
        ],
    )

    root = nv.Container(padding=50, child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="Expanded Cell"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
