"""Flow uniform grid demo showing tile layout with add/remove controls."""

from __future__ import annotations

from typing import List

from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.material.card import FilledCard, OutlinedCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import FilledTonalButton, OutlinedButton


class FlowUniformDemoModel:
    """ViewModel for the uniform Flow demo."""

    tiles: Observable[List[str]] = Observable([])

    def __init__(self) -> None:
        self.tiles.value = [
            "Task",
            "Idea",
            "Note",
            "Sketch",
            "Todo",
            "Review",
            "Plan",
            "Bug",
            "Demo",
        ]
        self._counter = len(self.tiles.value)

    def add_tile(self) -> None:
        tiles = list(self.tiles.value)
        self._counter += 1
        tiles.append(f"Tile {self._counter}")
        self.tiles.value = tiles

    def remove_tile(self) -> None:
        tiles = list(self.tiles.value)
        if not tiles:
            return
        tiles.pop()
        self.tiles.value = tiles


class FlowUniformDemo(ComposableWidget):
    """Widget tree for the uniform Flow demo."""

    def __init__(self, model: FlowUniformDemoModel | None = None) -> None:
        super().__init__()
        self.model = model or FlowUniformDemoModel()

    def _build_tile(self, label: str, idx: int) -> Widget:
        del idx
        return FilledCard(
            Column([Text(label), Text("Tap to edit")], gap=4, cross_alignment="start"),
            padding=12,
            style=CardStyle.filled().copy_with(border_radius=12),
            alignment="start",
        )

    def build(self) -> Widget:
        controls = Row(
            [
                FilledTonalButton("Add", on_click=self.model.add_tile),
                OutlinedButton("Remove", on_click=self.model.remove_tile),
            ],
            gap=8,
            cross_alignment="start",
        )

        flow = UniformFlow.builder(
            self.model.tiles,
            self._build_tile,
            columns=3,
            main_gap=12,
            cross_gap=12,
            padding=12,
            main_alignment="start",
            run_alignment="start",
            item_alignment=("stretch", "stretch"),
            aspect_ratio=1.0,
        )

        body = Column(
            [
                Text(
                    "Flow layout demo (uniform tiles)",
                ),
                controls,
                OutlinedCard(flow, padding=12, alignment="start"),
            ],
            gap=12,
            padding=12,
            cross_alignment="start",
        )

        return body


if __name__ == "__main__":
    demo = FlowUniformDemo()
    app = MaterialApp(content=demo, width=720, height=520)
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("flow_demo_uniform.png")
            print("Rendered flow_demo_uniform.png")
        except Exception:
            print("Flow uniform demo requires pyglet/skia to display or render output.")
