"""Material Widgets - ButtonGroup variants."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import (
    App,
    ConnectedButtonGroup,
    GroupButton,
    StandardButtonGroup,
    Text,
)
from nuiitivet.material.styles.button_group_style import (
    ConnectedButtonGroupStyle,
    StandardButtonGroupStyle,
)
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=12,
            cross_alignment="start",
            children=[
                Text("StandardButtonGroup (filled)"),
                StandardButtonGroup(
                    [
                        GroupButton("Day"),
                        GroupButton("Week"),
                        GroupButton("Month"),
                    ],
                ),
                Text("StandardButtonGroup (tonal, icons)"),
                StandardButtonGroup(
                    [
                        GroupButton(icon="format_align_left"),
                        GroupButton(icon="format_align_center"),
                        GroupButton(icon="format_align_right"),
                    ],
                    style=StandardButtonGroupStyle.tonal(),
                ),
                Text("ConnectedButtonGroup (single select)"),
                ConnectedButtonGroup(
                    [
                        GroupButton("Small"),
                        GroupButton("Medium"),
                        GroupButton("Large"),
                    ],
                    style=ConnectedButtonGroupStyle.outlined(),
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="ButtonGroup"),
        width=520,
        height=360,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
