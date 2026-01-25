import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    alignments = [
        "top-left",
        "top-center",
        "top-right",
        "center-left",
        "center",
        "center-right",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    ]

    def _tile(alignment: str) -> md.FilledCard:
        return md.FilledCard(
            md.Text(alignment, padding=8),
            width=160,
            height=96,
            alignment=alignment,
        )

    # Render all variants so differences are easy to compare.
    grid = nv.Flow(
        uniform=True,
        columns=3,
        main_gap=8,
        cross_gap=8,
        padding=8,
        children=[_tile(a) for a in alignments],
    )

    root = nv.Container(alignment="center", padding=24, child=grid)

    app = md.MaterialApp(
        content=root,
        title_bar=nv.DefaultTitleBar(title="nv.Container Alignment"),
        width="auto",
        height="auto",
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
