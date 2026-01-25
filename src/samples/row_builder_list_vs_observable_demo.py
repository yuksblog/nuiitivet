"""Row.builder demo: plain list vs Observable list.

Top: plain Python list (requires manual rebuild)
Bottom: Observable list (auto updates via subscription)
"""

from __future__ import annotations

from typing import List

from nuiitivet.observable import Observable
from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.material.buttons import FilledButton, OutlinedButton
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroller import Scroller
from nuiitivet.scrolling import ScrollDirection
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class _RowBuilderModel:
    plain_items: List[str]
    observable_items: Observable[List[str]] = Observable([])

    def __init__(self) -> None:
        self._plain_count = 2
        self._observable_count = 2

        self.plain_items = ["Plain 1", "Plain 2"]
        self.observable_items.value = ["Obs 1", "Obs 2"]

    def add_plain(self) -> None:
        self._plain_count += 1
        self.plain_items.append(f"Plain {self._plain_count}")

    def remove_plain(self) -> None:
        if self.plain_items:
            self.plain_items.pop()

    def add_observable(self) -> None:
        self._observable_count += 1
        items = list(self.observable_items.value)
        items.append(f"Obs {self._observable_count}")
        self.observable_items.value = items

    def remove_observable(self) -> None:
        items = list(self.observable_items.value)
        if not items:
            return
        items.pop()
        self.observable_items.value = items


class RowBuilderDemo(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.model = _RowBuilderModel()

    def build(self) -> Widget:
        return Column(
            [
                FilledCard(
                    Column(
                        [
                            Text("Row.builder with plain list (cannot update)"),
                            Row(
                                [
                                    FilledButton(
                                        "Add (Plain)",
                                        on_click=self._add_plain,
                                    ),
                                    OutlinedButton(
                                        "Remove (Plain)",
                                        on_click=self._remove_plain,
                                    ),
                                ],
                                gap=8,
                                cross_alignment="center",
                            ),
                            Scroller(
                                Row.builder(
                                    self.model.plain_items,
                                    lambda item, idx: Text(str(item)),
                                    gap=8,
                                    cross_alignment="center",
                                ),
                                direction=ScrollDirection.HORIZONTAL,
                                height=44,
                            ),
                        ],
                        gap=10,
                        cross_alignment="start",
                    ),
                    padding=12,
                    style=CardStyle.filled().copy_with(border_radius=8),
                    alignment="start",
                ),
                FilledCard(
                    Column(
                        [
                            Text("Row.builder with Observable list (can update)"),
                            Row(
                                [
                                    FilledButton(
                                        "Add (Observable)",
                                        on_click=self.model.add_observable,
                                    ),
                                    OutlinedButton(
                                        "Remove (Observable)",
                                        on_click=self.model.remove_observable,
                                    ),
                                ],
                                gap=8,
                                cross_alignment="center",
                            ),
                            Scroller(
                                Row.builder(
                                    self.model.observable_items,
                                    lambda item, idx: Text(str(item)),
                                    gap=8,
                                    cross_alignment="center",
                                ),
                                direction=ScrollDirection.HORIZONTAL,
                                height=44,
                            ),
                        ],
                        gap=10,
                        cross_alignment="start",
                    ),
                    padding=12,
                    style=CardStyle.filled().copy_with(border_radius=8),
                    alignment="start",
                ),
            ],
            gap=12,
            padding=16,
            cross_alignment="stretch",
        )

    def _add_plain(self) -> None:
        self.model.add_plain()
        self.invalidate()

    def _remove_plain(self) -> None:
        self.model.remove_plain()
        self.invalidate()


if __name__ == "__main__":
    widget = RowBuilderDemo()
    app = MaterialApp(content=widget)
    app.run()
