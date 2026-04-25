"""Visual demo for IconButton and IconToggleButton style presets."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Text
from nuiitivet.material import App
from nuiitivet.material.buttons import Fab, IconButton, IconToggleButton
from nuiitivet.material.styles import IconButtonStyle, IconToggleButtonStyle
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box


class IconButtonsDemoWidget:
    """Widget builder for icon button demo."""

    standard_selected = Observable(False)
    filled_selected = Observable(True)
    outlined_selected = Observable(False)
    tonal_selected = Observable(True)
    change_count = Observable(0)

    def _on_changed(self, _new_value: bool) -> None:
        self.change_count.value += 1

    def build(self):
        return Box(
            child=Column(
                [
                    Text("IconButton / IconToggleButton Demo"),
                    Text(self.change_count.map(lambda c: f"Toggle changes: {c}")),
                    Text(
                        self.standard_selected.combine(
                            self.filled_selected,
                            lambda a, b: f"standard={a}, filled={b}",
                        )
                    ),
                    Text(
                        self.outlined_selected.combine(
                            self.tonal_selected,
                            lambda a, b: f"outlined={a}, tonal={b}",
                        )
                    ),
                    Text("IconButton presets"),
                    Row(
                        [
                            IconButton("home", style=IconButtonStyle.standard()),
                            IconButton("favorite", style=IconButtonStyle.filled()),
                            IconButton("search", style=IconButtonStyle.outlined()),
                            IconButton("settings", style=IconButtonStyle.tonal()),
                            IconButton("add", style=IconButtonStyle.filled(), disabled=True),
                        ],
                        gap=12,
                    ),
                    Text("IconToggleButton presets"),
                    Row(
                        [
                            IconToggleButton(
                                "home",
                                selected=self.standard_selected,
                                on_change=self._on_changed,
                                style=IconToggleButtonStyle.standard(),
                            ),
                            IconToggleButton(
                                "favorite",
                                selected=self.filled_selected,
                                on_change=self._on_changed,
                                style=IconToggleButtonStyle.filled(),
                            ),
                            IconToggleButton(
                                "search",
                                selected=self.outlined_selected,
                                on_change=self._on_changed,
                                style=IconToggleButtonStyle.outlined(),
                            ),
                            IconToggleButton(
                                "settings",
                                selected=self.tonal_selected,
                                on_change=self._on_changed,
                                style=IconToggleButtonStyle.tonal(),
                            ),
                            IconToggleButton(
                                "add",
                                selected=True,
                                disabled=True,
                                style=IconToggleButtonStyle.filled(),
                            ),
                        ],
                        gap=12,
                    ),
                    Text("FAB (shape + expressive press)"),
                    Row(
                        [
                            Fab("add"),
                            Fab("edit"),
                            Fab("delete", disabled=True),
                        ],
                        gap=12,
                    ),
                ],
                gap=10,
                cross_alignment="start",
            ),
            padding=24,
            background_color="#F2F2F7",
        )


if __name__ == "__main__":
    demo = IconButtonsDemoWidget()
    app = App(content=demo.build())
    app.run()
