"""
Custom Dialog Usage (OverlayAware variant)

Shows how to use the OverlayAware mixin to let a custom dialog widget
close itself without requiring the caller to pass an Overlay reference.
"""

from nuiitivet.material import App
from nuiitivet.material.buttons import Button
from nuiitivet.material import Overlay
from nuiitivet.material.text import Text
from nuiitivet.material.card import Card
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.container import Container
from nuiitivet.layout.spacer import Spacer
from nuiitivet.observable import Observable
from nuiitivet.overlay import OverlayAware
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.material import ButtonStyle


class CounterDialog(ComposableWidget, OverlayAware[int]):
    """A self-contained dialog that closes itself via OverlayAware."""

    def __init__(self) -> None:
        super().__init__()
        self.counter = Observable(0)

    def _increment(self) -> None:
        self.counter.value += 1

    def _close(self) -> None:
        # No Overlay reference needed — the framework injected the handle.
        self.overlay_handle.close(self.counter.value)

    def build(self) -> Widget:
        return Card(
            child=Container(
                padding=24,
                child=Column(
                    gap=16,
                    children=[
                        Text("Self-Closing Dialog"),
                        Text("Uses OverlayAware to close itself."),
                        Row(
                            gap=10,
                            children=[
                                Text("Count:"),
                                Text(self.counter.map(str)),
                            ],
                        ),
                        Button("Increment", on_click=self._increment, style=ButtonStyle.filled()),
                        Spacer(height=8),
                        Button("Close & Return Count", on_click=self._close, style=ButtonStyle.outlined()),
                    ],
                ),
            ),
            width=300,
        )


class OverlayAwareDialogDemo(ComposableWidget):
    last_count: Observable[str] = Observable("No count yet")

    async def _show_custom_dialog(self):
        overlay = Overlay.root()

        # Caller no longer needs to pass the overlay into the dialog.
        result = await overlay.dialog(CounterDialog())

        if result.value is not None:
            self.last_count.value = f"Final Count: {result.value}"

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=20,
                children=[
                    Text(self.last_count),
                    Button(
                        "Open Self-Closing Dialog",
                        on_click=self._show_custom_dialog,
                        style=ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = ""):
    return App(content=OverlayAwareDialogDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
