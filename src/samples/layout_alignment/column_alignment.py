import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    main_alignments = [
        "start",
        "center",
        "end",
        "space-between",
    ]

    def _demo_column(alignment: str) -> nv.Column:
        # The column has a fixed height, so main-axis alignment is visible.
        return nv.Column(
            width="100%",
            height=250,
            gap=6,
            main_alignment=alignment,
            cross_alignment="center",
            children=[_tile("A"), _tile("B"), _tile("C")],
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
            width=150,
            padding=12,
        )

    content = nv.Column(
        # Render all variants side-by-side for easy comparison.
        children=[
            nv.Row(
                gap=12,
                main_alignment="start",
                cross_alignment="start",
                children=[_panel(a) for a in main_alignments],
            ),
        ],
        gap=12,
        padding=24,
        cross_alignment="start",
    )

    app = md.MaterialApp(
        content=content,
        title_bar=nv.DefaultTitleBar(title="nv.Column main_alignment"),
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
