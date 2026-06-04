"""Material Widgets - StandardSideSheet with Collapsible open/close."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Button, StandardSideSheet, Text
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


class StandardSideSheetDemo(nv.ComposableWidget):
    """Demo: main content area beside an openable StandardSideSheet."""

    opened: nv.Observable[bool] = nv.Observable(True)

    def toggle(self) -> None:
        self.opened.value = not self.opened.value

    def build(self) -> nv.Widget:
        sheet = Collapsible(
            StandardSideSheet(
                nv.Column(
                    padding=16,
                    gap=12,
                    width="100%",
                    children=[
                        Text("Option A"),
                        Text("Option B"),
                        Text("Option C"),
                    ],
                ),
                headline="Filters",
                on_close=self.toggle,
            ),
            opened=self.opened,
            axis="horizontal",
            alignment="top_right",
        )

        body = Box(
            nv.Column(
                padding=20,
                gap=12,
                children=[
                    Text("StandardSideSheet demo"),
                    Text("The sheet slides in from the right."),
                    Button("Toggle sheet", on_click=self.toggle),
                ],
            ),
            background_color=ColorRole.SURFACE,
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )

        return Row(
            [body, sheet],
            width=Sizing.flex(1),
            height=Sizing.flex(1),
        )


def main(png_path: str = "") -> None:
    app = App(
        content=StandardSideSheetDemo(),
        title="StandardSideSheet",
        width=600,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
