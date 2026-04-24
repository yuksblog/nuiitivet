"""
Basic Dialog Usage

Shows how to display a standard AlertDialog using Overlay.
"""

from nuiitivet.material import App
from nuiitivet.material.buttons import Button
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material import Overlay
from nuiitivet.material.text import Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.material import ButtonStyle


class BasicDialogDemo(ComposableWidget):
    result_text: Observable[str] = Observable("Ready")

    async def _show_dialog(self):
        # Overlay.root() finds the globally unique Overlay
        overlay = Overlay.root()

        # Create the dialog widget
        dialog = AlertDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[
                Button(
                    "CANCEL",
                    on_click=lambda: overlay.close("Canceled"),
                    style=ButtonStyle.text()),
                Button(
                    "OK",
                    on_click=lambda: overlay.close("Confirmed"),
                    style=ButtonStyle.text()),
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
                    Button(
                        "Show Alert Dialog",
                        on_click=self._show_dialog,
                        style=ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        # For screenshot, render the dialog directly
        dialog = AlertDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[Button("CANCEL", style=ButtonStyle.text()), Button("OK", style=ButtonStyle.text())],
        )
        app = App(content=Container(alignment="center", child=dialog), width=400, height=300)
        app.render_to_png(png_path)
        return app

    return App(content=BasicDialogDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
