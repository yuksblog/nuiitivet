"""
ViewModel Direct Usage (Coupled)

Shows a ViewModel pattern where the ViewModel depends directly on UI components (AlertDialog).
This is simpler but creates strong coupling between Logic and View.
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


class CoupledViewModel:
    """A ViewModel that knows about UI widgets (Simple but coupled)."""

    def __init__(self):
        self.status = Observable("Ready")

    async def process_action(self, overlay: MaterialOverlay):
        self.status.value = "Processing..."

        # ViewModel creates and configures the View (AlertDialog)
        dialog = AlertDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[
                TextButton("OK", on_click=lambda: overlay.close(True)),
            ],
        )

        await overlay.dialog(dialog)
        self.status.value = "Finished"


class DirectViewModelDemo(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = CoupledViewModel()

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
        # Screenshot: Render the dialog that the ViewModel would create
        dialog = AlertDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[TextButton("OK")],
        )
        app = MaterialApp(content=Container(alignment="center", child=dialog), width=400, height=300)
        app.render_to_png(png_path)
        return app

    return MaterialApp(content=DirectViewModelDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
