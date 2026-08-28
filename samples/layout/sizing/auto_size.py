import nuiitivet.material as nv


def main(png: str = ""):
    widget = nv.Card(
        # width/height 指定なし -> auto
        width="auto",
        height="auto",
        child=nv.Text("This box fits the content"),
        padding=16,
        alignment="center",
    )

    root = nv.Container(alignment="center", child=widget)

    app = nv.App(nv.Window(content=root, title="Auto Size", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
