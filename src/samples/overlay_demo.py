"""Overlay Demo - Snackbar and AlertDialog examples.

This demo shows how to use the Overlay system:
- Snackbar messages with auto-removal
- AlertDialog with custom content and actions
"""

from nuiitivet.material.app import MaterialApp
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material import Text
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class OverlayDemo(ComposableWidget):
    """Demo widget showing Overlay features."""

    snackbar_count: Observable[int] = Observable(0)
    dialog_result: Observable[str] = Observable("No dialog shown yet")

    def __init__(self):
        super().__init__()

    def show_snackbar(self):
        """Show a simple snackbar message."""
        self.snackbar_count.value += 1
        MaterialOverlay.root().snackbar(f"Snackbar #{self.snackbar_count.value}")

    def show_long_snackbar(self):
        """Show a snackbar with longer duration."""
        MaterialOverlay.root().snackbar("This snackbar lasts 5 seconds", duration=5.0)

    def show_info_dialog(self):
        """Show an information dialog."""

        def on_ok():
            self.dialog_result.value = "Info dialog: OK clicked"
            MaterialOverlay.root().close_topmost()

        MaterialOverlay.root().dialog(
            AlertDialog(
                title="Information",
                message="This is an information dialog.",
                actions=[
                    FilledButton("OK", on_click=on_ok),
                ],
            )
        )

    def show_confirm_dialog(self):
        """Show a confirmation dialog."""

        def on_cancel():
            self.dialog_result.value = "Confirm dialog: Cancelled"
            MaterialOverlay.root().close_topmost()

        def on_confirm():
            self.dialog_result.value = "Confirm dialog: Confirmed"
            MaterialOverlay.root().close_topmost()

        MaterialOverlay.root().dialog(
            AlertDialog(
                title="Confirm Action",
                message="Are you sure you want to proceed?",
                actions=[
                    TextButton("Cancel", on_click=on_cancel),
                    FilledButton("Confirm", on_click=on_confirm),
                ],
            )
        )

    def show_custom_dialog(self):
        """Show a dialog with custom styling."""

        def on_close():
            self.dialog_result.value = "Custom dialog: Closed"
            MaterialOverlay.root().close_topmost()

        from nuiitivet.material.styles.dialog_style import DialogStyle

        MaterialOverlay.root().dialog(
            AlertDialog(
                title="Custom Dialog",
                message="This dialog has custom content.\nMultiple lines are supported.",
                actions=[
                    FilledButton("Close", on_click=on_close),
                ],
                style=DialogStyle(
                    min_width=400.0,
                    padding=32,
                    corner_radius=16.0,
                    background=(240, 248, 255, 255),  # Alice blue
                ),
            )
        )

    def build(self) -> Widget:
        """Build the demo widget tree."""
        return Container(
            padding=32,
            child=Column(
                children=[
                    Text("Overlay Demo"),
                    # Snackbar section
                    Text("Snackbar Messages:"),
                    FilledButton("Show Snackbar", on_click=self.show_snackbar),
                    FilledButton("Show Long Snackbar (5s)", on_click=self.show_long_snackbar),
                    # Dialog section
                    Text("Alert Dialogs:"),
                    FilledButton("Show Info Dialog", on_click=self.show_info_dialog),
                    FilledButton("Show Confirm Dialog", on_click=self.show_confirm_dialog),
                    FilledButton("Show Custom Dialog", on_click=self.show_custom_dialog),
                    # Result display
                    Text("Last Dialog Result:"),
                    Text(self.dialog_result),
                ],
                gap=16,
                cross_alignment="start",
            ),
        )


def main():
    """Run the overlay demo."""
    app = MaterialApp(content=OverlayDemo(), width=600, height=700)
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Error running demo: {e}")
