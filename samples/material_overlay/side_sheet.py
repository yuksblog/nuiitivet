"""
Side Sheet Usage

Shows how to display a modal side sheet using Overlay.side_sheet().
"""

from __future__ import annotations

import nuiitivet.material as nv


class SideSheetDemo(nv.ComposableWidget):
    def show_side_sheet(self) -> None:
        nv.Overlay.root().side_sheet(
            nv.SideSheet(
                nv.Box(
                    nv.Column(
                        children=[
                            nv.HorizontalDivider(),
                            nv.Text("Setting 1"),
                            nv.Text("Setting 2"),
                            nv.Text("Setting 3"),
                        ],
                        gap=12,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Settings",
            )
        )

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Side Sheet Demo"),
                    nv.Button("Open Settings", on_click=self.show_side_sheet, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = "") -> nv.App:
    if png_path:
        background = nv.Container(
            alignment="center",
            width="100%",
            height="100%",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Side Sheet Demo"),
                    nv.Button("Open Settings", style=nv.ButtonStyle.filled()),
                ],
            ),
        )
        scrim = nv.Box(
            background_color=(0, 0, 0, 80),
            width="100%",
            height="100%",
        )
        sheet_overlay = nv.Container(
            alignment="top-right",
            width="100%",
            height="100%",
            child=nv.SideSheet(
                nv.Box(
                    nv.Column(
                        children=[
                            nv.HorizontalDivider(),
                            nv.Text("Setting 1"),
                            nv.Text("Setting 2"),
                            nv.Text("Setting 3"),
                        ],
                        gap=12,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Settings",
            ),
        )
        app = nv.App(
            content=nv.Stack(width=640, height=400, children=[background, scrim, sheet_overlay]),
            width=640,
            height=400,
        )
        app.render_to_png(png_path)
        return app

    return nv.App(content=SideSheetDemo(), width=640, height=400)


if __name__ == "__main__":
    main().run()
