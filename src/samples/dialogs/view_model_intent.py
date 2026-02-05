"""
ViewModel Intent Usage

Shows how to trigger a standard AlertDialog using an Intent from a ViewModel-like structure.
This decouples the presentation logic (ViewModel) from the View implementation.
"""

from nuiitivet.material.app import MaterialApp
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.intents import AlertDialogIntent
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.text import Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class DecoupledViewModel:
    """A ViewModel that manages state and logic, decoupled from UI widgets."""

    def __init__(self):
        self.status = Observable("Ready")

    async def process_action(self, overlay: MaterialOverlay):
        self.status.value = "Processing..."

        # Express the intent to show an operation complete dialog
        intent = AlertDialogIntent(
            title="Operation Complete", message="Process finished successfully.", icon="check_circle"
        )

        await overlay.dialog(intent)
        self.status.value = "Finished"


class IntentDemo(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = DecoupledViewModel()

    async def _on_run_click(self):
        overlay = MaterialOverlay.root()
        await self.vm.process_action(overlay)

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=20,
                children=[
                    Text(self.vm.status),
                    FilledButton(
                        "Run Process",
                        on_click=self._on_run_click,
                    ),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        dialog = AlertDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[TextButton("OK")],
        )
        app = MaterialApp(content=Container(alignment="center", child=dialog), width=400, height=300)
        app.render_to_png(png_path)
        return app

    return MaterialApp(content=IntentDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
