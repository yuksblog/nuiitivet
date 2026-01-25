"""App layout grid sample."""

from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def _card(label: str, width="100%", height="100%") -> md.FilledCard:
    return md.FilledCard(
        md.Text(label),
        padding=12,
        alignment="center",
        width=width,
        height=height,
    )


def main(png: str = ""):
    header = nv.GridItem(_card("Header"), row=0, column=[0, 1])
    # Sidebar width is "auto" (content based), so we disable explicit flex/size
    sidebar = nv.GridItem(_card("Sidebar", width=None), row=[1, 2], column=0)
    content = nv.GridItem(_card("Main content"), row=1, column=1)
    # Footer height is "auto" (content based)
    footer = nv.GridItem(_card("Footer", height=None), row=2, column=1)

    widget = nv.Grid(
        rows=[60, "100%", "auto"],
        columns=["auto", "100%"],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[header, sidebar, content, footer],
    )

    # 400x400 as requested
    # title_bar argument included so render_layout_images.py can extract the title string
    app = md.MaterialApp(
        content=widget,
        title_bar=nv.DefaultTitleBar(title="nv.Grid Layout"),
        width=400,
        height=400,
    )

    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
