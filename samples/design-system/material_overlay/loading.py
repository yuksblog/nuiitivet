"""
Loading Indicator Usage

Shows how to display a centered loading indicator using Overlay.loading().
"""

from __future__ import annotations

import nuiitivet.material as nv


class LoadingDemo(nv.ComposableWidget):
    def show_loading(self) -> None:
        nv.Overlay.of(self).loading()
        # handle = Overlay.of(self).loading()
        # In real usage, dismiss when done:
        # handle.close(None)

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Loading Demo"),
                    nv.Button("Show Loading", on_click=self.show_loading, style=nv.ButtonStyle.tonal()),
                ],
            ),
        )


def main(png_path: str = "") -> nv.App:
    if png_path:
        background = nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Loading Demo"),
                    nv.Button("Show Loading", style=nv.ButtonStyle.tonal()),
                ],
            ),
        )
        indicator_overlay = nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.LoadingIndicator(size=48),
        )
        app = nv.App(
            content=nv.Stack(width=480, height=320, children=[background, indicator_overlay]),
            width=480,
            height=320,
        )
        app.render_to_png(png_path)
        return app

    return nv.App(content=LoadingDemo(), width=480, height=320)


if __name__ == "__main__":
    main().run()
