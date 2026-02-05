"""
Custom Dialog Usage

Shows how to display any generic Widget as a modal dialog using MaterialOverlay.
"""

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

    def __init__(self, overlay: MaterialOverlay):
        super().__init__()
        self.overlay = overlay
        self.counter = Observable(0)

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
                        Text("You can maintain state within the dialog."),
                        Row(
                            gap=10,
                            children=[
                                Text("Count:"),
                                Text(self.counter.map(str)),
                            ],
                        ),
                        FilledButton("Increment", on_click=self._increment),
                        Spacer(height=8),
                        OutlinedButton("Close & Return Count", on_click=lambda: self.overlay.close(self.counter.value)),
                    ],
                ),
            ),
            width=300,
        )


class CustomDialogDemo(ComposableWidget):
    last_count: Observable[str] = Observable("No count yet")

    async def _show_custom_dialog(self):
        overlay = MaterialOverlay.root()

        # Pass the overlay instance to the content so it can close itself
        content = CustomDialogContent(overlay)

        # Show any widget. It will be centered with a scrim by default.
        result = await overlay.dialog(content)

        if result.value is not None:
            self.last_count.value = f"Final Count: {result.value}"

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Column(
                gap=20,
                children=[
                    Text(self.last_count),
                    FilledButton(
                        "Open Custom Dialog",
                        on_click=self._show_custom_dialog,
                    ),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        from typing import cast

        # Mock overlay for screenshot
        content = CustomDialogContent(overlay=cast(MaterialOverlay, None))
        content.counter.value = 5
        app = MaterialApp(content=Container(alignment="center", child=content), width=400, height=300)
        app.render_to_png(png_path)
        return app

    return MaterialApp(content=CustomDialogDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
