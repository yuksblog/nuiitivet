"""Material Widgets - NavigationRail."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Card, CardStyle, NavigationRail, RailItem, Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import Sizing


def main(png_path: str = "") -> None:
    rail = NavigationRail(
        children=[
            RailItem(icon="home", label="Home", small_badge=Observable(True)),
            RailItem(icon="search", label="Search", large_badge=Observable("3")),
            RailItem(icon="library_books", label="Library"),
            RailItem(icon="settings", label="Settings"),
        ],
        index=Observable(0),
        expanded=Observable(False),
        show_menu_button=True,
        height=Sizing.flex(1),
    )
    body = Card(
        Column(
            gap=8,
            padding=20,
            cross_alignment="start",
            children=[
                Text("NavigationRail"),
                Text("Compact, expanded, badges, and menu button."),
            ],
        ),
        style=CardStyle.filled().copy_with(border_radius=0),
        width=Sizing.flex(1),
        height=Sizing.flex(1),
    )
    app = App(
        content=Row([rail, body], width=Sizing.flex(1), height=Sizing.flex(1)),
        title_bar=nv.DefaultTitleBar(title="NavigationRail"),
        width=560,
        height=320,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
