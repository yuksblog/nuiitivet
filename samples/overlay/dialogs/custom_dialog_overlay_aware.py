"""
Custom Dialog Usage (OverlayAware variant)

Shows how to use the OverlayAware mixin to let a custom dialog widget
close itself without requiring the caller to pass an Overlay reference.
"""

import nuiitivet.material as nv


class CounterDialog(nv.ComposableWidget, nv.OverlayAware[int]):
    """A self-contained dialog that closes itself via OverlayAware."""

    def __init__(self) -> None:
        super().__init__()
        self.counter = nv.Observable(0)

    def _increment(self) -> None:
        self.counter.value += 1

    def _close(self) -> None:
        # No Overlay reference needed — the framework injected the handle.
        self.overlay_handle.close(self.counter.value)

    def build(self) -> nv.Widget:
        return nv.Card(
            child=nv.Container(
                padding=24,
                child=nv.Column(
                    gap=16,
                    children=[
                        nv.Text("Self-Closing Dialog"),
                        nv.Text("Uses OverlayAware to close itself."),
                        nv.Row(
                            gap=10,
                            children=[
                                nv.Text("Count:"),
                                nv.Text(self.counter.map(str)),
                            ],
                        ),
                        nv.Button("Increment", on_click=self._increment, style=nv.ButtonStyle.filled()),
                        nv.Spacer(height=8),
                        nv.Button("Close & Return Count", on_click=self._close, style=nv.ButtonStyle.outlined()),
                    ],
                ),
            ),
            width=300,
        )


class OverlayAwareDialogDemo(nv.ComposableWidget):
    last_count: nv.Observable[str] = nv.Observable("No count yet")

    async def _show_custom_dialog(self):
        overlay = nv.Overlay.of(self)

        # Caller no longer needs to pass the overlay into the dialog.
        result = await overlay.dialog(CounterDialog())

        if result.value is not None:
            self.last_count.value = f"Final Count: {result.value}"

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=20,
                children=[
                    nv.Text(self.last_count),
                    nv.Button(
                        "Open Self-Closing Dialog",
                        on_click=self._show_custom_dialog,
                        style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = ""):
    return nv.App(nv.Window(content=OverlayAwareDialogDemo(), width=400, height=300))


if __name__ == "__main__":
    main().run()
