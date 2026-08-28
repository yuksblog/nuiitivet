import nuiitivet.material as nv


def main(png: str = "") -> None:
    def _tile(label: str, *, width: int = 160, height: int = 40) -> nv.Card:
        return nv.Card(
            nv.Text(label),
            width=width,
            height=height,
            alignment="center",
        )

    # Column with cross_alignment="start"; individual children override via CrossAligned.
    content = nv.Column(
        width=300,
        gap=8,
        cross_alignment="start",
        padding=24,
        children=[
            _tile("start (default)"),
            nv.CrossAligned(_tile("center (override)"), "center"),
            _tile("start (default)"),
            nv.CrossAligned(_tile("end (override)"), "end"),
        ],
    )

    app = nv.App(nv.Window(content=content, title="nv.CrossAligned", width="auto", height="auto"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
