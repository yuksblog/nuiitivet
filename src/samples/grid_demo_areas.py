"""Grid sample demonstrating named area placement."""

from __future__ import annotations

from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.material import Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.card import FilledCard
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import ComposableWidget, Widget


def _card(label: str) -> FilledCard:
    return FilledCard(
        Text(label),
        padding=12,
        alignment="center",
        width=Sizing.flex(1),
        height=Sizing.flex(1),
    )


class GridDemo(ComposableWidget):

    def build(self) -> Widget:
        return Grid.named_areas(
            rows=[60, Sizing.flex(1), "auto"],
            columns=[240, Sizing.flex(1)],
            areas=[
                ["header", "header"],
                ["sidebar", "content"],
                ["footer", "content"],
            ],
            row_gap=12,
            column_gap=12,
            padding=12,
            children=[
                GridItem.named_area(_card("Header"), name="header"),
                GridItem.named_area(_card("Sidebar"), name="sidebar"),
                GridItem.named_area(_card("Main content"), name="content"),
                GridItem.named_area(_card("Footer"), name="footer"),
            ],
        )


if __name__ == "__main__":
    demo = GridDemo()
    app = MaterialApp(content=demo, width=640, height=480)
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("grid_demo.png")
            print("Rendered grid_demo.png")
        except Exception:
            print("Grid demo requires pyglet/skia to display or render output.")
