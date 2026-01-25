import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    cross_alignments = [
        "start",
        "center",
        "end",
    ]

    def _demo_column(alignment: str) -> nv.Column:
        # The tiles are full-width, so cross-axis alignment is visible.
        return nv.Column(
            width="100%",
            gap=6,
            main_alignment="start",
            cross_alignment=alignment,
            children=[_tile("W=72"), _tile("W=72"), _tile("W=72")],
        )

    def _tile(label: str, *, width: int = 72, height: int = 32) -> md.FilledCard:
        return md.FilledCard(
            md.Text(label),
            width=width,
            height=height,
            alignment="center",
        )

    def _panel(alignment: str) -> md.OutlinedCard:
        return md.OutlinedCard(
            nv.Column(
                children=[md.Text(alignment), _demo_column(alignment)],
                gap=8,
                cross_alignment="start",
                width="100%",
            ),
            width=200,
            padding=12,
        )

    content = nv.Column(
        # Render all variants side-by-side for easy comparison.
        children=[
            nv.Row(
                gap=12,
                main_alignment="start",
                cross_alignment="start",
                children=[_panel(a) for a in cross_alignments],
            ),
        ],
        gap=12,
        padding=24,
        cross_alignment="start",
    )

    app = md.MaterialApp(
        content=content,
        title_bar=nv.DefaultTitleBar(title="nv.Column cross_alignment"),
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
