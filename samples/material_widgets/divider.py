"""Material Widgets - Divider horizontal/vertical."""

from __future__ import annotations

from nuiitivet.material import App, HorizontalDivider, Text, VerticalDivider
from nuiitivet.material.styles.divider_style import DividerStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def main(png_path: str = "") -> None:
    list_section = Column(
        cross_alignment="start",
        children=[
            Text("Inbox", padding=(8, 8, 8, 8)),
            HorizontalDivider(),
            Text("Sent", padding=(8, 8, 8, 8)),
            HorizontalDivider(style=DividerStyle(inset_left=24)),
            Text("Drafts", padding=(8, 8, 8, 8)),
        ],
    )

    row_section = Row(
        height=40,
        cross_alignment="center",
        children=[
            Text("Home", padding=(16, 8, 16, 8)),
            VerticalDivider(),
            Text("Explore", padding=(16, 8, 16, 8)),
            VerticalDivider(),
            Text("Account", padding=(16, 8, 16, 8)),
        ],
    )

    content = Container(
        padding=24,
        child=Column(
            gap=20,
            cross_alignment="start",
            children=[
                Text("Horizontal Divider"),
                list_section,
                Text("Vertical Divider"),
                row_section,
            ],
        ),
    )
    app = App(
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
