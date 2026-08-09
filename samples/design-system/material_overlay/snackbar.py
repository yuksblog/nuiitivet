"""
Snackbar Usage

Shows how to display a brief, non-blocking message using Overlay.snackbar().
"""

from __future__ import annotations

import nuiitivet.material as nv


class SnackbarDemo(nv.ComposableWidget):
    def show_snackbar(self) -> None:
        nv.Overlay.root().snackbar("Item deleted")

    def show_custom_snackbar(self) -> None:
        nv.Overlay.root().snackbar(nv.Snackbar("Upload complete"))

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Snackbar Demo"),
                    nv.Button("Show Snackbar", on_click=self.show_snackbar, style=nv.ButtonStyle.filled()),
                    nv.Button("Custom Snackbar", on_click=self.show_custom_snackbar, style=nv.ButtonStyle.outlined()),
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
                    nv.Text("Snackbar Demo"),
                    nv.Button("Show Snackbar", style=nv.ButtonStyle.filled()),
                    nv.Button("Custom Snackbar", style=nv.ButtonStyle.outlined()),
                ],
            ),
        )
        snackbar_overlay = nv.Container(
            alignment="bottom-center",
            width="wt",
            height="wt",
            padding=(0, 0, 0, 24),
            child=nv.Snackbar("Item deleted"),
        )
        app = nv.App(
            content=nv.Stack(width=480, height=320, children=[background, snackbar_overlay]),
            width=480,
            height=320,
        )
        app.render_to_png(png_path)
        return app

    return nv.App(content=SnackbarDemo(), width=480, height=320)


if __name__ == "__main__":
    main().run()
