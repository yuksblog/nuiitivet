"""Material Widgets - Card filled/outlined/elevated."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Card, CardStyle, Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def _card(label: str, style: CardStyle) -> Card:
    return Card(
        Column(gap=4, children=[Text(label), Text("Card body content")]),
        width=160,
        height=110,
        padding=16,
        style=style,
    )


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Row(
            gap=16,
            children=[
                _card("Filled", CardStyle.filled()),
                _card("Outlined", CardStyle.outlined()),
                _card("Elevated", CardStyle.elevated()),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="Card"),
        width=600,
        height=220,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
