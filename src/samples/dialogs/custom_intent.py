"""
Custom Intent Usage

Shows how to define a custom Intent and Intent Handler.
This allows the ViewModel to request complex interactions (like a Yes/No confirmation)
without knowing about the specific UI implementation (Widgets).
"""

from dataclasses import dataclass
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.buttons import FilledButton, OutlinedButton
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.text import Text
from nuiitivet.material.card import Card
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.container import Container
from nuiitivet.layout.spacer import Spacer
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class CustomDialogContent(ComposableWidget):
    """A completely custom widget to be used as a dialog."""

    def __init__(self, overlay: MaterialOverlay, initial: int = 0):
        super().__init__()
        self.overlay = overlay
        self.counter = Observable(initial)

    def _increment(self):
        self.counter.value += 1

    def build(self) -> Widget:
        return Card(
            child=Container(
                padding=24,
                child=Column(
                    gap=16,
                    children=[
                        Text("Custom Interactive Dialog"),
                        Row(
                            gap=10,
                            children=[Text("Count:"), Text(self.counter.map(str))],
                        ),
                        FilledButton("Increment", on_click=self._increment),
                        Spacer(height=8),
                        OutlinedButton("Close & Return Count", on_click=lambda: self.overlay.close(self.counter.value)),
                    ],
                ),
            ),
            width=300,
        )


# 1. Define the Custom Intent (Plain Data)
@dataclass(frozen=True)
class CounterIntent:
    """Intent to request a counter value from user."""

    initial_value: int = 0


# 2. Define the Dialog Creator
def create_counter_dialog(intent: CounterIntent) -> Widget:
    """Creates a widget for the CounterIntent."""
    return CustomDialogContent(
        MaterialOverlay.root(),
        initial=intent.initial_value,
    )


class CustomIntentViewModel:
    def __init__(self):
        self.message = Observable("No result yet")

    async def open_counter(self, overlay: MaterialOverlay):
        # The ViewModel just emits an intent and waits for a result
        result = await overlay.dialog(CounterIntent(initial_value=5))

        if result.value is not None:
            self.message.value = f"Final Count from Intent: {result.value}"


class CustomIntentDemo(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = CustomIntentViewModel()

    async def _on_open_click(self):
        overlay = MaterialOverlay.root()
        await self.vm.open_counter(overlay)

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=20,
                children=[
                    Text(self.vm.message),
                    FilledButton(
                        "Open Counter (via Intent)",
                        on_click=self._on_open_click,
                    ),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        from typing import cast

        content = CustomDialogContent(overlay=cast(MaterialOverlay, None), initial=5)
        app = MaterialApp(content=Container(alignment="center", child=content), width=400, height=300)
        app.render_to_png(png_path)
        return app

    # 3. Register the Mapping in MaterialApp
    return MaterialApp(
        content=CustomIntentDemo(),
        overlay_routes={CounterIntent: create_counter_dialog},
        width=400,
        height=300,
    )


if __name__ == "__main__":
    main().run()
