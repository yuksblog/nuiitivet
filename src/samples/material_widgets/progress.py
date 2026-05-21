"""Material Widgets - Progress and loading indicators."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import (
    App,
    CircularProgressIndicator,
    IndeterminateCircularProgressIndicator,
    IndeterminateLinearProgressIndicator,
    LinearProgressIndicator,
    LoadingIndicator,
    Text,
)
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                Text("LinearProgressIndicator"),
                LinearProgressIndicator(value=0.4, width=320),
                Text("Indeterminate Linear"),
                IndeterminateLinearProgressIndicator(width=320),
                Text("Circular (determinate / indeterminate)"),
                Row(
                    gap=24,
                    cross_alignment="center",
                    children=[
                        CircularProgressIndicator(value=0.65, size=40),
                        IndeterminateCircularProgressIndicator(size=40),
                        LoadingIndicator(),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="Progress Indicators"),
        width=440,
        height=320,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
