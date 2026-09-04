"""
ViewModel Intent Usage

Shows how to trigger a standard BasicDialog using an Intent from a ViewModel-like structure.
This decouples the presentation logic (ViewModel) from the View implementation.
"""

import nuiitivet.material as nv


class DecoupledViewModel:
    """A ViewModel that manages state and logic, decoupled from UI widgets."""

    def __init__(self):
        self.status = nv.Observable("Ready")

    async def process_action(self, overlay: nv.OverlayProtocol):
        self.status.value = "Processing..."

        # Express the intent to show an operation complete dialog
        intent = nv.BasicDialogIntent(
            title="Operation Complete", message="Process finished successfully.", icon="check_circle"
        )

        await overlay.dialog(intent)
        self.status.value = "Finished"


class IntentDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = DecoupledViewModel()

    async def _on_run_click(self):
        # Resolve here, not in __init__: a widget has no ancestors until mounted.
        await self.vm.process_action(nv.Overlay.of(self))

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=20,
                children=[
                    nv.Text(self.vm.status),
                    nv.Button("Run Process", on_click=self._on_run_click, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    if png_path:
        dialog = nv.BasicDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[nv.Button("OK", style=nv.ButtonStyle.text())],
        )
        app = nv.App(nv.Window(content=nv.Container(alignment="center", child=dialog), width=400, height=300))
        app.render_to_png(png_path)
        return

    app = nv.App(nv.Window(content=IntentDemo(), width=400, height=300))
    app.run()


if __name__ == "__main__":
    main()
