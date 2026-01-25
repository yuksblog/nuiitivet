"""Visual demo for disabled button states."""

from nuiitivet.material.app import MaterialApp
from nuiitivet.observable import Observable
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Text
from nuiitivet.material.buttons import FilledButton, TextButton, OutlinedButton, ElevatedButton, FilledTonalButton


class DisabledButtonDemoWidget:
    """Widget builder for disabled button demo."""

    click_count = Observable(0)

    def increment(self):
        """Increment click counter."""
        self.click_count.value += 1

    def build(self):
        return Column(
            [
                Text(self.click_count.map(lambda c: f"Click count: {c}")),
                Text("Only enabled buttons respond to clicks"),
                Row(
                    [
                        FilledButton("Enabled", on_click=self.increment, width=150),
                        FilledButton("Disabled", on_click=self.increment, disabled=True, width=150),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        TextButton("Enabled Text", on_click=self.increment, width=150),
                        TextButton("Disabled Text", on_click=self.increment, disabled=True, width=150),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        OutlinedButton("Enabled Outlined", on_click=self.increment, width=150),
                        OutlinedButton("Disabled Outlined", on_click=self.increment, disabled=True, width=150),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        ElevatedButton("Enabled Elevated", on_click=self.increment, width=150),
                        ElevatedButton("Disabled Elevated", on_click=self.increment, disabled=True, width=150),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        FilledTonalButton("Enabled Tonal", on_click=self.increment, width=150),
                        FilledTonalButton("Disabled Tonal", on_click=self.increment, disabled=True, width=150),
                    ],
                    gap=20,
                ),
                Text("Disabled buttons appear at 38% opacity (Material Design 3)"),
            ],
            gap=15,
        )


if __name__ == "__main__":
    demo = DisabledButtonDemoWidget()
    app = MaterialApp(content=demo.build())
    app.run()
