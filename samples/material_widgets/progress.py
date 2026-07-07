"""Material Widgets - Progress and loading indicators."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.Text("LinearProgressIndicator"),
                nv.LinearProgressIndicator(value=0.4, width=320),
                nv.Text("Indeterminate Linear"),
                nv.IndeterminateLinearProgressIndicator(width=320),
                nv.Text("Circular (determinate / indeterminate)"),
                nv.Row(
                    gap=24,
                    cross_alignment="center",
                    children=[
                        nv.CircularProgressIndicator(value=0.65, size=40),
                        nv.IndeterminateCircularProgressIndicator(size=40),
                        nv.LoadingIndicator(),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(
        content=content,
        title="Progress Indicators",
        width=440,
        height=320,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
