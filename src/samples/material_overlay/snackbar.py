"""
Snackbar Usage

Shows how to display a brief, non-blocking message using Overlay.snackbar().
"""

from __future__ import annotations

from nuiitivet.material import App, Overlay, Text, Button, ButtonStyle
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class SnackbarDemo(ComposableWidget):
    def show_snackbar(self) -> None:
        Overlay.root().snackbar("Item deleted")

    def show_custom_snackbar(self) -> None:
        Overlay.root().snackbar(Snackbar("Upload complete"))

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=16,
                children=[
                    Text("Snackbar Demo"),
                    Button("Show Snackbar", on_click=self.show_snackbar, style=ButtonStyle.filled()),
                    Button("Custom Snackbar", on_click=self.show_custom_snackbar, style=ButtonStyle.outlined()),
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
                    Text("Snackbar Demo"),
                    Button("Show Snackbar", style=ButtonStyle.filled()),
                    Button("Custom Snackbar", style=ButtonStyle.outlined()),
                ],
            ),
        )
        snackbar_overlay = Container(
            alignment="bottom-center",
            width="100%",
            height="100%",
            padding=(0, 0, 0, 24),
            child=Snackbar("Item deleted"),
        )
        app = App(
            content=Stack(width=480, height=320, children=[background, snackbar_overlay]),
            width=480,
            height=320,
        )
        app.render_to_png(png_path)
        return app

    return App(content=SnackbarDemo(), width=480, height=320)


if __name__ == "__main__":
    main().run()
