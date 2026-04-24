"""Visual demo for disabled button states."""

from nuiitivet.material import App
from nuiitivet.observable import Observable
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Text
from nuiitivet.material.buttons import Button
from nuiitivet.material import ButtonStyle


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
                        Button("Enabled", on_click=self.increment, width=150, style=ButtonStyle.filled()),
                        Button("Disabled", on_click=self.increment, disabled=True,
                               width=150, style=ButtonStyle.filled()),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        Button("Enabled Text", on_click=self.increment, width=150, style=ButtonStyle.text()),
                        Button("Disabled Text", on_click=self.increment,
                               disabled=True, width=150, style=ButtonStyle.text()),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        Button("Enabled Outlined", on_click=self.increment, width=150, style=ButtonStyle.outlined()),
                        Button("Disabled Outlined", on_click=self.increment,
                               disabled=True, width=150, style=ButtonStyle.outlined()),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        Button("Enabled Elevated", on_click=self.increment, width=150, style=ButtonStyle.elevated()),
                        Button("Disabled Elevated", on_click=self.increment,
                               disabled=True, width=150, style=ButtonStyle.elevated()),
                    ],
                    gap=20,
                ),
                Row(
                    [
                        Button("Enabled Tonal", on_click=self.increment, width=150, style=ButtonStyle.tonal()),
                        Button("Disabled Tonal", on_click=self.increment,
                               disabled=True, width=150, style=ButtonStyle.tonal()),
                    ],
                    gap=20,
                ),
                Text("Disabled buttons appear at 38% opacity (Material Design 3)"),
            ],
            gap=15,
        )


if __name__ == "__main__":
    demo = DisabledButtonDemoWidget()
    app = App(content=demo.build())
    app.run()
