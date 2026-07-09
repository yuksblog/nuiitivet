"""Material Widgets - Divider horizontal/vertical."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    list_section = nv.Column(
        cross_alignment="start",
        children=[
            nv.Text("Inbox", padding=(8, 8, 8, 8)),
            nv.HorizontalDivider(),
            nv.Text("Sent", padding=(8, 8, 8, 8)),
            nv.HorizontalDivider(style=nv.DividerStyle(inset_left=24)),
            nv.Text("Drafts", padding=(8, 8, 8, 8)),
        ],
    )

    row_section = nv.Row(
        height=40,
        cross_alignment="center",
        children=[
            nv.Text("Home", padding=(16, 8, 16, 8)),
            nv.VerticalDivider(),
            nv.Text("Explore", padding=(16, 8, 16, 8)),
            nv.VerticalDivider(),
            nv.Text("Account", padding=(16, 8, 16, 8)),
        ],
    )

    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=20,
            cross_alignment="start",
            children=[
                nv.Text("Horizontal Divider"),
                list_section,
                nv.Text("Vertical Divider"),
                row_section,
            ],
        ),
    )
    app = nv.App(
        content=content,
        title="Divider",
        width=440,
        height=360,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
