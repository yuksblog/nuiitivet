"""Material Widgets - NavigationRail."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    rail = nv.NavigationRail(
        children=[
            nv.RailItem(icon="home", label="Home", small_badge=nv.Observable(True)),
            nv.RailItem(icon="search", label="Search", large_badge=nv.Observable("3")),
            nv.RailItem(icon="library_books", label="Library"),
            nv.RailItem(icon="settings", label="Settings"),
        ],
        index=nv.Observable(0),
        expanded=nv.Observable(False),
        show_menu_button=True,
    )
    body = nv.Card(
        nv.Column(
            gap=8,
            padding=20,
            cross_alignment="start",
            children=[
                nv.Text("NavigationRail"),
                nv.Text("Compact, expanded, badges, and menu button."),
            ],
        ),
        style=nv.CardStyle.filled().copy_with(border_radius=0),
        width="wt",
        height="wt",
    )
    app = nv.App(
        content=nv.Row([rail, body], width="wt", height="wt"),
        title="NavigationRail",
        width=560,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
