"""Interactive demo highlighting scope-local rebuilds.

Run with:
    PYTHONPATH=src uv run python src/samples/scope_partial_rebuild.py
"""

from __future__ import annotations

from nuiitivet.material.app import MaterialApp
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material import Text
from nuiitivet.material.styles.text_style import TextStyle


class ScopedCountersDemo(ComposableWidget):
    left_count = Observable(0)
    right_count = Observable(0)

    def __init__(self) -> None:
        super().__init__(padding=16)
        self._left_scope: str | None = None
        self._right_scope: str | None = None
        self._left_builds = 0
        self._right_builds = 0

    def build(self) -> Widget:
        with self.scope("left_counter") as left_handle:
            self._left_scope = left_handle.id
            left_panel = self.render_scope_with_handle(left_handle, self._build_left_panel)
        with self.scope("right_counter") as right_handle:
            self._right_scope = right_handle.id
            right_panel = self.render_scope_with_handle(right_handle, self._build_right_panel)

        controls = Row(
            [
                FilledButton("Increment Left", on_click=self._increment_left),
                FilledButton("Increment Right", on_click=self._increment_right),
                TextButton("Reset", on_click=self._reset),
            ],
            gap=12,
            cross_alignment="center",
        )

        return Column(
            [left_panel, right_panel, controls],
            padding=20,
            gap=20,
            cross_alignment="center",
        )

    def _build_left_panel(self) -> Widget:
        self._left_builds += 1
        return self._build_panel("Left", self.left_count.value, self._left_builds)

    def _build_right_panel(self) -> Widget:
        self._right_builds += 1
        return self._build_panel("Right", self.right_count.value, self._right_builds)

    def _build_panel(self, label: str, value: int, builds: int) -> Widget:
        return FilledCard(
            child=Column(
                [
                    Text(f"{label} scope value: {value}", padding=(0, 0, 0, 4)),
                    Text(f"Build count: {builds}", padding=(0, 0, 0, 4), style=TextStyle(color="#6750A4")),
                ],
                gap=4,
                cross_alignment="start",
            ),
            padding=16,
            width=None,
            height=None,
            style=CardStyle.filled().copy_with(
                background="#F3F0F5",
                border_radius=12,
            ),
        )

    def _increment_left(self) -> None:
        self.left_count.value += 1
        if self._left_scope:
            self.invalidate_scope_id(self._left_scope)

    def _increment_right(self) -> None:
        self.right_count.value += 1
        if self._right_scope:
            self.invalidate_scope_id(self._right_scope)

    def _reset(self) -> None:
        self.left_count.value = 0
        self.right_count.value = 0
        if self._left_scope:
            self.invalidate_scope_id(self._left_scope)
        if self._right_scope:
            self.invalidate_scope_id(self._right_scope)


def main() -> None:
    demo = ScopedCountersDemo()
    app = MaterialApp(content=demo)
    app.run()


if __name__ == "__main__":
    main()
