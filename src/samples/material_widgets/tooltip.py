"""Material Widgets - Tooltip and RichTooltip rendered inline."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, RichTooltip, Text, Tooltip
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=20,
            cross_alignment="start",
            children=[
                Text("Tooltip (plain)"),
                Tooltip("Save the current document"),
                Text("RichTooltip"),
                RichTooltip(
                    supporting_text="Saves your work and uploads it to the cloud.",
                    subhead="Save changes",
                    action_label="Learn more",
                    action_label_2="Dismiss",
                    width=340,
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="Tooltip"),
        width=440,
        height=320,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
