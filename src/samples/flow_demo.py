"""Flow layout demo showing wrapping behavior with variable-width items."""

from __future__ import annotations

from typing import List

from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.material.card import OutlinedCard
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import FilledTonalButton, OutlinedButton
from nuiitivet.material.styles import TextStyle
from nuiitivet.runtime.title_bar import DefaultTitleBar


class FlowDemoModel:
    """ViewModel for the Flow demo."""

    tags: Observable[List[str]] = Observable([])

    def __init__(self) -> None:
        self.tags.value = [
            "Python",
            "UI",
            "Nuiitivet",
            "Layout",
            "Flow",
            "Wrap",
            "Responsive",
            "Desktop",
            "Framework",
            "Widget",
            "Material Design",
            "Composition",
            "Declarative",
        ]

    def add_tag(self) -> None:
        tags = list(self.tags.value)
        tags.append(f"Tag {len(tags) + 1}")
        self.tags.value = tags

    def remove_tag(self) -> None:
        tags = list(self.tags.value)
        if not tags:
            return
        tags.pop()
        self.tags.value = tags


class FlowDemo(ComposableWidget):
    """Widget tree for the Flow demo."""

    def __init__(self, model: FlowDemoModel | None = None) -> None:
        super().__init__()
        self.model = model or FlowDemoModel()

    def _build_tag(self, label: str, idx: int) -> Widget:
        # Variable width implied by text content
        return OutlinedCard(
            Text(label),
            padding=(16, 8, 16, 8),
            alignment="center",
        )

    def build(self) -> Widget:
        controls = Row(
            [
                FilledTonalButton("Add Tag", on_click=self.model.add_tag),
                OutlinedButton("Remove Tag", on_click=self.model.remove_tag),
            ],
            gap=8,
            cross_alignment="center",
        )

        # Flow using builder for Observable list
        flow = Flow.builder(
            self.model.tags,
            self._build_tag,
            main_gap=8,
            cross_gap=8,
            padding=16,
            main_alignment="start",
            cross_alignment="center",
        )

        body = Column(
            [
                Text("Flow Layout (Wrapping)", style=TextStyle(font_size=24)),
                Text("Resize window to see wrapping behavior."),
                controls,
                OutlinedCard(flow, padding=0, width="100%", height="auto"),
            ],
            gap=16,
            padding=24,
            height="auto",
        )

        return body


if __name__ == "__main__":
    demo = FlowDemo()
    app = MaterialApp(
        content=demo,
        width=600,
        height=500,
        title_bar=DefaultTitleBar(title="Flow Demo"),
    )
    try:
        app.run()
    except Exception:
        pass
