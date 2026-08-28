"""
Bottom Sheet Usage

Shows how to display a modal bottom sheet using Overlay.bottom_sheet().
"""

from __future__ import annotations

import nuiitivet.material as nv


class BottomSheetDemo(nv.ComposableWidget):
    def show_bottom_sheet(self) -> None:
        nv.Overlay.of(self).bottom_sheet(
            nv.BottomSheet(
                nv.Box(
                    nv.Column(
                        children=[
                            nv.HorizontalDivider(),
                            nv.Text("Item 1"),
                            nv.Text("Item 2"),
                            nv.Text("Item 3"),
                        ],
                        gap=8,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Options",
            )
        )

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Bottom Sheet Demo"),
                    nv.Button("Show Bottom Sheet", on_click=self.show_bottom_sheet, style=nv.ButtonStyle.filled()),
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
                    nv.Text("Bottom Sheet Demo"),
                    nv.Button("Show Bottom Sheet", style=nv.ButtonStyle.filled()),
                ],
            ),
        )
        scrim = nv.Box(
            background_color=(0, 0, 0, 80),
            width="wt",
            height="wt",
        )
        sheet_overlay = nv.Container(
            alignment="bottom-center",
            width="wt",
            height="wt",
            child=nv.BottomSheet(
                nv.Box(
                    nv.Column(
                        children=[
                            nv.HorizontalDivider(),
                            nv.Text("Item 1"),
                            nv.Text("Item 2"),
                            nv.Text("Item 3"),
                        ],
                        gap=8,
                        cross_alignment="start",
                    ),
                    padding=24,
                ),
                headline="Options",
            ),
        )
        app = nv.App(
            nv.Window(
                content=nv.Stack(width=480, height=400, children=[background, scrim, sheet_overlay]),
                width=480,
                height=400,
            )
        )
        app.render_to_png(png_path)
        return app

    return nv.App(nv.Window(content=BottomSheetDemo(), width=480, height=400))


if __name__ == "__main__":
    main().run()
