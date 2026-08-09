"""
ViewModel Direct Usage (Coupled)

Shows a ViewModel pattern where the ViewModel depends directly on UI components (BasicDialog).
This is simpler but creates strong coupling between Logic and View.
"""

import nuiitivet.material as nv


class CoupledViewModel:
    """A ViewModel that knows about UI widgets (Simple but coupled)."""

    def __init__(self):
        self.status = nv.Observable("Ready")

    async def process_action(self, overlay: nv.Overlay):
        self.status.value = "Processing..."

        # ViewModel creates and configures the View (BasicDialog)
        dialog = nv.BasicDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[
                nv.Button("OK", on_click=lambda: overlay.close(True), style=nv.ButtonStyle.text()),
            ],
        )

        await overlay.dialog(dialog)
        self.status.value = "Finished"


class DirectViewModelDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = CoupledViewModel()

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


def main(png_path: str = ""):
    if png_path:
        # Screenshot: Render the dialog that the ViewModel would create
        dialog = nv.BasicDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[nv.Button("OK", style=nv.ButtonStyle.text())],
        )
        app = nv.App(content=nv.Container(alignment="center", child=dialog), width=400, height=300)
        app.render_to_png(png_path)
        return app

    return nv.App(content=DirectViewModelDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
