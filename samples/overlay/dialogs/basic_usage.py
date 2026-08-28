"""
Basic Dialog Usage

Shows how to display a standard BasicDialog using Overlay.
"""

import nuiitivet.material as nv


class BasicDialogDemo(nv.ComposableWidget):
    result_text: nv.Observable[str] = nv.Observable("Ready")

    async def _show_dialog(self):
        # No Overlay is nested above this screen, so this resolves to the App's.
        overlay = nv.Overlay.of(self)

        # Create the dialog widget
        dialog = nv.BasicDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[
                nv.Button("CANCEL", on_click=lambda: overlay.close("Canceled"), style=nv.ButtonStyle.text()),
                nv.Button("OK", on_click=lambda: overlay.close("Confirmed"), style=nv.ButtonStyle.text()),
            ],
        )

        # Show the dialog and await the result
        # The result is an OverlayResult[T]
        result = await overlay.dialog(dialog)

        if result.value:
            self.result_text.value = f"Last Action: {result.value}"

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=20,
                children=[
                    nv.Text(self.result_text),
                    nv.Button("Show Basic Dialog", on_click=self._show_dialog, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        # For screenshot, render the dialog directly
        dialog = nv.BasicDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[nv.Button("CANCEL", style=nv.ButtonStyle.text()), nv.Button("OK", style=nv.ButtonStyle.text())],
        )
        app = nv.App(nv.Window(content=nv.Container(alignment="center", child=dialog), width=400, height=300))
        app.render_to_png(png_path)
        return app

    return nv.App(nv.Window(content=BasicDialogDemo(), width=400, height=300))


if __name__ == "__main__":
    main().run()
