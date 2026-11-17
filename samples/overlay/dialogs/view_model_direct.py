"""
ViewModel Direct Usage (Coupled)

Shows a ViewModel pattern where the ViewModel depends directly on UI components (BasicDialog).
This is simpler but creates strong coupling between Logic and View.
"""

import nuiitivet.material as nv


class CoupledViewModel:
    """A ViewModel that knows about UI widgets (Simple but coupled)."""

    def __init__(self, overlay: nv.OverlayProtocol):
        self._overlay = overlay
        self.status = nv.State("Ready")

    async def process_action(self):
        self.status.value = "Processing..."

        # ViewModel creates and configures the View (BasicDialog)
        dialog = nv.BasicDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[
                nv.Button("OK", on_click=lambda: self._overlay.close(True), style=nv.ButtonStyle.text()),
            ],
        )

        await self._overlay.dialog(dialog)
        self.status.value = "Finished"


class DirectViewModelDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = CoupledViewModel(nv.Overlay.proxy(self))

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=20,
                children=[
                    nv.Text(self.vm.status),
                    nv.Button("Run Process", on_click=self.vm.process_action, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    if png_path:
        # Screenshot: Render the dialog that the ViewModel would create
        dialog = nv.BasicDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[nv.Button("OK", style=nv.ButtonStyle.text())],
        )
        app = nv.App(nv.Window(content=nv.Container(alignment="center", child=dialog), width=400, height=300))
        app.render_to_png(png_path)
        return

    app = nv.App(nv.Window(content=DirectViewModelDemo, width=400, height=300))
    app.run()


if __name__ == "__main__":
    main()
