import nuiitivet as nv
import nuiitivet.material as md


def _tile(label: str) -> md.FilledCard:
    return md.FilledCard(
        md.Text(label),
        width=56,
        height=40,
        alignment="center",
    )


def main(png: str = ""):
    main_alignments = [
        "start",
        "center",
        "end",
        "space-between",
        "space-around",
        "space-evenly",
    ]

    def _demo_row(alignment: str) -> nv.Row:
        # The row stretches to full width, so main-axis alignment is visible.
        return nv.Row(
            width="100%",
            gap=8,
            main_alignment=alignment,
            cross_alignment="center",
            children=[_tile("A"), _tile("B"), _tile("C")],
        )

    content = nv.Column(
        # Render all variants so differences are easy to compare.
        children=[
            md.OutlinedCard(
                nv.Column(
                    children=[md.Text(a), _demo_row(a)],
                    gap=8,
                    cross_alignment="start",
                    width="100%",
                ),
                width=560,
                padding=12,
            )
            for a in main_alignments
        ],
        gap=12,
        padding=24,
        cross_alignment="start",
    )

    app = md.MaterialApp(
        content=content,
        title_bar=nv.DefaultTitleBar(title="nv.Row main_alignment"),
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
