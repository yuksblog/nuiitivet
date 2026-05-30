"""
Loading Indicator Usage

Shows how to display a centered loading indicator using Overlay.loading().
"""

from __future__ import annotations

from nuiitivet.material import App, Overlay, Text, Button, ButtonStyle, LoadingIndicator
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class LoadingDemo(ComposableWidget):
    def show_loading(self) -> None:
        Overlay.root().loading()
        # handle = Overlay.root().loading()
        # In real usage, dismiss when done:
        # handle.close(None)

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=16,
                children=[
                    Text("Loading Demo"),
                    Button("Show Loading", on_click=self.show_loading, style=ButtonStyle.tonal()),
                ],
            ),
        )


def main(png_path: str = "") -> App:
    if png_path:
        background = Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Column(
                gap=16,
                children=[
                    Text("Loading Demo"),
                    Button("Show Loading", style=ButtonStyle.tonal()),
                ],
            ),
        )
        indicator_overlay = Container(
            alignment="center",
            width="100%",
            height="100%",
            child=LoadingIndicator(size=48),
        )
        app = App(
            content=Stack(width=480, height=320, children=[background, indicator_overlay]),
            width=480,
            height=320,
        )
        app.render_to_png(png_path)
        return app

    return App(content=LoadingDemo(), width=480, height=320)


if __name__ == "__main__":
    main().run()
