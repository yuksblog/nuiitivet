"""Overlay Demo - Snackbar and AlertDialog examples.

This demo shows how to use the Overlay system:
- Snackbar messages with auto-removal
- AlertDialog with custom content and actions
"""

import logging

from nuiitivet.material.app import MaterialApp
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material import Text
from nuiitivet.widgeting.widget import ComposableWidget, Widget


logger = logging.getLogger(__name__)


class OverlayDemo(ComposableWidget):
    """Demo widget showing Overlay features."""

    snackbar_count: Observable[int] = Observable(0)
    dialog_result: Observable[str] = Observable("No dialog shown yet")

    def __init__(self):
        super().__init__()

    def show_snackbar(self):
        """Show a simple snackbar message."""
        self.snackbar_count.value += 1
        overlay = MaterialOverlay.root()
        logger.warning("[overlay-demo] show_snackbar before entries=%s", overlay.has_entries())
        overlay.snackbar(f"Snackbar #{self.snackbar_count.value}")
        logger.warning("[overlay-demo] show_snackbar after entries=%s", overlay.has_entries())

    def show_long_snackbar(self):
        """Show a snackbar with longer duration."""
        overlay = MaterialOverlay.root()
        logger.warning("[overlay-demo] show_long_snackbar before entries=%s", overlay.has_entries())
        overlay.snackbar("This snackbar lasts 5 seconds", duration=5.0)
        logger.warning("[overlay-demo] show_long_snackbar after entries=%s", overlay.has_entries())

    def show_info_dialog(self):
        """Show an information dialog."""
        overlay = MaterialOverlay.root()
        logger.warning("[overlay-demo] show_info_dialog begin entries=%s", overlay.has_entries())

        def on_ok():
            self.dialog_result.value = "Info dialog: OK clicked"
            logger.warning("[overlay-demo] info_dialog on_ok close_topmost")
            overlay.close_topmost()

        overlay.dialog(
            AlertDialog(
                title="Information",
                message="This is an information dialog.",
                actions=[
                    FilledButton("OK", on_click=on_ok),
                ],
            )
        )
        logger.warning("[overlay-demo] show_info_dialog end entries=%s", overlay.has_entries())

    def show_confirm_dialog(self):
        """Show a confirmation dialog."""
        overlay = MaterialOverlay.root()
        logger.warning("[overlay-demo] show_confirm_dialog begin entries=%s", overlay.has_entries())

        def on_cancel():
            self.dialog_result.value = "Confirm dialog: Cancelled"
            logger.warning("[overlay-demo] confirm_dialog cancel close_topmost")
            overlay.close_topmost()

        def on_confirm():
            self.dialog_result.value = "Confirm dialog: Confirmed"
            logger.warning("[overlay-demo] confirm_dialog confirm close_topmost")
            overlay.close_topmost()

        overlay.dialog(
            AlertDialog(
                title="Confirm Action",
                message="Are you sure you want to proceed?",
                actions=[
                    TextButton("Cancel", on_click=on_cancel),
                    FilledButton("Confirm", on_click=on_confirm),
                ],
            )
        )
        logger.warning("[overlay-demo] show_confirm_dialog end entries=%s", overlay.has_entries())

    def show_custom_dialog(self):
        """Show a dialog with custom styling."""
        overlay = MaterialOverlay.root()
        logger.warning("[overlay-demo] show_custom_dialog begin entries=%s", overlay.has_entries())

        def on_close():
            self.dialog_result.value = "Custom dialog: Closed"
            logger.warning("[overlay-demo] custom_dialog close_topmost")
            overlay.close_topmost()

        from nuiitivet.material.styles.dialog_style import DialogStyle

        overlay.dialog(
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
        logger.warning("[overlay-demo] show_custom_dialog end entries=%s", overlay.has_entries())

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
