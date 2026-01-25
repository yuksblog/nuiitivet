import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    cross_alignments = [
        "start",
        "center",
        "end",
    ]

    def _demo_row(alignment: str) -> nv.Row:
        # The row has a fixed height, so cross-axis alignment is visible.
        return nv.Row(
            width="100%",
            height=120,
            gap=8,
            main_alignment="start",
            cross_alignment=alignment,
            children=[_bar("H=32", 32), _bar("H=64", 64), _bar("H=96", 96)],
        )

    def _bar(label: str, height: int) -> md.FilledCard:
        return md.FilledCard(
            md.Text(label),
            width=88,
            height=height,
            alignment="center",
        )

    def _panel(alignment: str) -> md.OutlinedCard:
        return md.OutlinedCard(
            nv.Column(
                children=[md.Text(alignment), _demo_row(alignment)],
                gap=8,
                cross_alignment="start",
                width="100%",
            ),
            width=560,
            padding=12,
        )

    content = nv.Column(
        # Render all variants so differences are easy to compare.
        children=[_panel(a) for a in cross_alignments],
        gap=12,
        padding=24,
        cross_alignment="start",
    )

    app = md.MaterialApp(
        content=content,
        title_bar=nv.DefaultTitleBar(title="nv.Row cross_alignment"),
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
