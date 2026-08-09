"""
Custom Intent Usage

Shows how to define a custom Intent and Intent Handler.
This allows the ViewModel to request complex interactions (like a Yes/No confirmation)
without knowing about the specific UI implementation (Widgets).
"""

from dataclasses import dataclass
import nuiitivet.material as nv


class CustomDialogContent(nv.ComposableWidget):
    """A completely custom widget to be used as a dialog."""

    def __init__(self, initial: int = 0):
        super().__init__()
        self.counter = nv.Observable(initial)

    def _increment(self):
        self.counter.value += 1

    def _close(self):
        # An overlay route is mounted inside the overlay showing it, so the
        # nearest ancestor Overlay is exactly the one to close.
        nv.Overlay.of(self).close(self.counter.value)

    def build(self) -> nv.Widget:
        return nv.Card(
            child=nv.Container(
                padding=24,
                child=nv.Column(
                    gap=16,
                    children=[
                        nv.Text("Custom Interactive Dialog"),
                        nv.Row(
                            gap=10,
                            children=[nv.Text("Count:"), nv.Text(self.counter.map(str))],
                        ),
                        nv.Button("Increment", on_click=self._increment, style=nv.ButtonStyle.filled()),
                        nv.Spacer(height=8),
                        nv.Button("Close & Return Count", on_click=self._close, style=nv.ButtonStyle.outlined()),
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
def create_counter_dialog(intent: CounterIntent) -> nv.Widget:
    """Creates a widget for the CounterIntent."""
    return CustomDialogContent(initial=intent.initial_value)


class CustomIntentViewModel:
    def __init__(self):
        self.message = nv.Observable("No result yet")

    async def open_counter(self, overlay: nv.OverlayProtocol):
        # The ViewModel just emits an intent and waits for a result
        result = await overlay.dialog(CounterIntent(initial_value=5))

        if result.value is not None:
            self.message.value = f"Final Count from Intent: {result.value}"


class CustomIntentDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = CustomIntentViewModel()

    async def _on_open_click(self):
        # Resolve here, not in __init__: a widget has no ancestors until mounted.
        await self.vm.open_counter(nv.Overlay.of(self))

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=20,
                children=[
                    nv.Text(self.vm.message),
                    nv.Button(
                        "Open Counter (via Intent)",
                        on_click=self._on_open_click,
                        style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        content = CustomDialogContent(initial=5)
        app = nv.App(content=nv.Container(alignment="center", child=content), width=400, height=300)
        app.render_to_png(png_path)
        return app

    # 3. Register the Mapping in App
    return nv.App(
        content=CustomIntentDemo(),
        overlay_routes={CounterIntent: create_counter_dialog},
        width=400,
        height=300,
    )


if __name__ == "__main__":
    main().run()
