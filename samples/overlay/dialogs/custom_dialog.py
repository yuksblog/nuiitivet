"""
Custom Dialog Usage

Shows how to display any generic Widget as a modal dialog using Overlay.
"""

import nuiitivet.material as nv


class CustomDialogContent(nv.ComposableWidget):
    """A completely custom widget to be used as a dialog."""

    def __init__(self, overlay: nv.Overlay):
        super().__init__()
        self.overlay = overlay
        self.counter = nv.Observable(0)

    def _increment(self):
        self.counter.value += 1

    def build(self) -> nv.Widget:
        return nv.Card(
            child=nv.Container(
                padding=24,
                child=nv.Column(
                    gap=16,
                    children=[
                        nv.Text("Custom Interactive Dialog"),
                        nv.Text("You can maintain state within the dialog."),
                        nv.Row(
                            gap=10,
                            children=[
                                nv.Text("Count:"),
                                nv.Text(self.counter.map(str)),
                            ],
                        ),
                        nv.Button("Increment", on_click=self._increment, style=nv.ButtonStyle.filled()),
                        nv.Spacer(height=8),
                        nv.Button("Close & Return Count", on_click=lambda: self.overlay.close(
                            self.counter.value), style=nv.ButtonStyle.outlined()),
                    ],
                ),
            ),
            width=300,
        )


class CustomDialogDemo(nv.ComposableWidget):
    last_count: nv.Observable[str] = nv.Observable("No count yet")

    async def _show_custom_dialog(self):
        overlay = nv.Overlay.of(self)

        # Pass the overlay instance to the content so it can close itself
        content = CustomDialogContent(overlay)

        # Show any widget. It will be centered with a scrim by default.
        result = await overlay.dialog(content)

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
                        "Open Custom Dialog",
                        on_click=self._show_custom_dialog,
                        style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = ""):
    if png_path:
        from typing import cast

        # Mock overlay for screenshot
        content = CustomDialogContent(overlay=cast(nv.Overlay, None))
        content.counter.value = 5
        app = nv.App(content=nv.Container(alignment="center", child=content), width=400, height=300)
        app.render_to_png(png_path)
        return app

    return nv.App(content=CustomDialogDemo(), width=400, height=300)


if __name__ == "__main__":
    main().run()
