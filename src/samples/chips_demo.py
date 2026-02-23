"""Visual demo for Material Design 3 chip widgets."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import AssistChip, FilterChip, InputChip, SuggestionChip, Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.observable import Observable


class ChipsDemoWidget:
    """Widget builder for chip demo."""

    filter_selected = Observable(False)
    status = Observable("Ready")

    def on_assist_click(self) -> None:
        """Handle assist chip click."""
        self.status.value = "AssistChip clicked"

    def on_filter_change(self, selected: bool) -> None:
        """Handle filter chip selected-state changes."""
        self.status.value = f"FilterChip selected: {selected}"

    def on_input_click(self) -> None:
        """Handle input chip click.

        Note:
            Chip itself does not remove data. Developers can implement removal
            by updating external Observable state in this callback.
        """
        self.status.value = "InputChip clicked (remove/update is controlled by app Observable)"

    def on_input_trailing_icon_click(self) -> None:
        """Handle input chip trailing icon click."""
        self.status.value = "InputChip trailing icon clicked"

    def on_suggestion_click(self) -> None:
        """Handle suggestion chip click."""
        self.status.value = "SuggestionChip clicked"

    def build(self) -> Column:
        """Build demo widget tree."""
        return Column(
            [
                Text("Material 3 Chip Demo"),
                Text("FilterChip selected is Observable-backed"),
                Row(
                    [
                        AssistChip("Assist", leading_icon="add", on_click=self.on_assist_click),
                        FilterChip(
                            "Filter",
                            selected=self.filter_selected,
                            on_selected_change=self.on_filter_change,
                            leading_icon="tune",
                        ),
                    ],
                    gap=12,
                ),
                Row(
                    [
                        InputChip(
                            "Input",
                            leading_icon="person",
                            trailing_icon="close",
                            on_trailing_icon_click=self.on_input_trailing_icon_click,
                            on_click=self.on_input_click,
                        ),
                        SuggestionChip(
                            "Suggestion",
                            leading_icon="lightbulb",
                            on_click=self.on_suggestion_click,
                        ),
                    ],
                    gap=12,
                ),
                Text(self.status),
            ],
            gap=12,
            padding=20,
        )


def main() -> None:
    """Run chip demo."""
    demo = ChipsDemoWidget()
    app = MaterialApp(content=demo.build())
    app.run()


if __name__ == "__main__":
    main()
