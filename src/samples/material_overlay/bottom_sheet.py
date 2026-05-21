"""
Bottom Sheet Usage

Shows how to display a modal bottom sheet using Overlay.bottom_sheet().
"""

from __future__ import annotations

from nuiitivet.material import App, Overlay, Text, Button, ButtonStyle, Divider, BottomSheet
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class BottomSheetDemo(ComposableWidget):
    def show_bottom_sheet(self) -> None:
        Overlay.root().bottom_sheet(
            BottomSheet(
                Box(
                    Column(
                        children=[
                            Divider(),
                            Text("Item 1"),
                            Text("Item 2"),
                            Text("Item 3"),
                        ],
                        gap=8,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Options",
            )
        )

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=16,
                children=[
                    Text("Bottom Sheet Demo"),
                    Button("Show Bottom Sheet", on_click=self.show_bottom_sheet, style=ButtonStyle.filled()),
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
                    Text("Bottom Sheet Demo"),
                    Button("Show Bottom Sheet", style=ButtonStyle.filled()),
                ],
            ),
        )
        scrim = Box(
            background_color=(0, 0, 0, 80),
            width="100%",
            height="100%",
        )
        sheet_overlay = Container(
            alignment="bottom-center",
            width="100%",
            height="100%",
            child=BottomSheet(
                Box(
                    Column(
                        children=[
                            Divider(),
                            Text("Item 1"),
                            Text("Item 2"),
                            Text("Item 3"),
                        ],
                        gap=8,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Options",
            ),
        )
        app = App(
            content=Stack(width=480, height=400, children=[background, scrim, sheet_overlay]),
            width=480,
            height=400,
        )
        app.render_to_png(png_path)
        return app

    return App(content=BottomSheetDemo(), width=480, height=400)


if __name__ == "__main__":
    main().run()
