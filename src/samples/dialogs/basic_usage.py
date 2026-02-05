"""
Basic Dialog Usage

Shows how to display a standard AlertDialog using MaterialOverlay.
"""

from nuiitivet.material.app import MaterialApp
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.text import Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class BasicDialogDemo(ComposableWidget):
    result_text: Observable[str] = Observable("Ready")

    async def _show_dialog(self):
        # MaterialOverlay.root() finds the globally unique Overlay
        overlay = MaterialOverlay.root()

        # Create the dialog widget
        dialog = AlertDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[
                TextButton(
                    "CANCEL",
                    on_click=lambda: overlay.close("Canceled"),
                ),
                TextButton(
                    "OK",
                    on_click=lambda: overlay.close("Confirmed"),
                ),
            ],
        )

        # Show the dialog and await the result
        # The result is an OverlayResult[T]
        result = await overlay.dialog(dialog)

        if result.value:
            self.result_text.value = f"Last Action: {result.value}"

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=20,
                children=[
                    Text(self.result_text),
                    FilledButton(
                        "Show Alert Dialog",
                        on_click=self._show_dialog,
                    ),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        # For screenshot, render the dialog directly
        dialog = AlertDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[TextButton("CANCEL"), TextButton("OK")],
        )
        app = MaterialApp(content=Container(alignment="center", child=dialog), width=400, height=300)
        app.render_to_png(png_path)
        return app

    return MaterialApp(content=BasicDialogDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
