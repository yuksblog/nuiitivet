"""Visual demo for Material toggle button variants."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Text
from nuiitivet.material import App
from nuiitivet.material.buttons import ToggleButton
from nuiitivet.observable import Observable
from nuiitivet.material import ToggleButtonStyle


class ToggleButtonsDemoWidget:
    """Widget builder for toggle button demo."""

    filled_selected = Observable(False)
    outlined_selected = Observable(True)
    text_selected = Observable(False)
    tonal_selected = Observable(True)
    change_count = Observable(0)

    def _on_changed(self, _new_value: bool) -> None:
        self.change_count.value += 1

    def build(self):
        return Column(
            [
                Text("Toggle Button Demo"),
                Text(self.change_count.map(lambda c: f"Changed: {c}")),
                Text(
                    self.filled_selected.combine(
                        self.outlined_selected,
                        lambda a, b: f"Filled={a}, Outlined={b}",
                    )
                ),
                Text(
                    self.text_selected.combine(
                        self.tonal_selected,
                        lambda a, b: f"Text={a}, Tonal={b}",
                    )
                ),
                Row(
                    [
                        ToggleButton(
                            "Filled",
                            icon="check",
                            selected=self.filled_selected,
                            on_change=self._on_changed,
                            width=170,
                            style=ToggleButtonStyle.filled(),
                        ),
                        ToggleButton(
                            "Filled Disabled",
                            icon="check",
                            selected=True,
                            disabled=True,
                            width=170,
                            style=ToggleButtonStyle.filled(),
                        ),
                    ],
                    gap=16,
                ),
                Row(
                    [
                        ToggleButton(
                            "Outlined",
                            icon="check",
                            selected=self.outlined_selected,
                            on_change=self._on_changed,
                            width=170,
                            style=ToggleButtonStyle.outlined(),
                        ),
                        ToggleButton(
                            "Outlined Disabled",
                            icon="check",
                            selected=False,
                            disabled=True,
                            width=170,
                            style=ToggleButtonStyle.outlined(),
                        ),
                    ],
                    gap=16,
                ),
                Row(
                    [
                        ToggleButton(
                            "Text",
                            icon="check",
                            selected=self.text_selected,
                            on_change=self._on_changed,
                            width=170,
                            style=ToggleButtonStyle.outlined(),
                        ),
                        ToggleButton(
                            "Text Disabled",
                            icon="check",
                            selected=True,
                            disabled=True,
                            width=170,
                            style=ToggleButtonStyle.outlined(),
                        ),
                    ],
                    gap=16,
                ),
                Row(
                    [
                        ToggleButton(
                            "Tonal",
                            icon="check",
                            selected=self.tonal_selected,
                            on_change=self._on_changed,
                            width=170,
                            style=ToggleButtonStyle.tonal(),
                        ),
                        ToggleButton(
                            "Tonal Disabled",
                            icon="check",
                            selected=False,
                            disabled=True,
                            width=170,
                            style=ToggleButtonStyle.tonal(),
                        ),
                    ],
                    gap=16,
                ),
                Text("Each click toggles selected state and updates on_change callback count."),
            ],
            gap=12,
        )


if __name__ == "__main__":
    demo = ToggleButtonsDemoWidget()
    app = App(content=demo.build())
    app.run()
