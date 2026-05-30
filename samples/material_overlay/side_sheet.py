"""
Side Sheet Usage

Shows how to display a modal side sheet using Overlay.side_sheet().
"""

from __future__ import annotations

from nuiitivet.material import App, Overlay, Text, Button, ButtonStyle, Divider, SideSheet
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class SideSheetDemo(ComposableWidget):
    def show_side_sheet(self) -> None:
        Overlay.root().side_sheet(
            SideSheet(
                Box(
                    Column(
                        children=[
                            Divider(),
                            Text("Setting 1"),
                            Text("Setting 2"),
                            Text("Setting 3"),
                        ],
                        gap=12,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Settings",
            )
        )

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=16,
                children=[
                    Text("Side Sheet Demo"),
                    Button("Open Settings", on_click=self.show_side_sheet, style=ButtonStyle.filled()),
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
                    Text("Side Sheet Demo"),
                    Button("Open Settings", style=ButtonStyle.filled()),
                ],
            ),
        )
        scrim = Box(
            background_color=(0, 0, 0, 80),
            width="100%",
            height="100%",
        )
        sheet_overlay = Container(
            alignment="top-right",
            width="100%",
            height="100%",
            child=SideSheet(
                Box(
                    Column(
                        children=[
                            Divider(),
                            Text("Setting 1"),
                            Text("Setting 2"),
                            Text("Setting 3"),
                        ],
                        gap=12,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Settings",
            ),
        )
        app = App(
            content=Stack(width=640, height=400, children=[background, scrim, sheet_overlay]),
            width=640,
            height=400,
        )
        app.render_to_png(png_path)
        return app

    return App(content=SideSheetDemo(), width=640, height=400)


if __name__ == "__main__":
    main().run()
