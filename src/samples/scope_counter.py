from __future__ import annotations

from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import FilledButton, TextButton


class ScopeCounterDemo(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.left_value = 0
        self.right_value = 0
        self._left_scope_id: str | None = None
        self._right_scope_id: str | None = None

    def build(self) -> Widget:
        with self.scope("left_counter") as left_handle:
            self._left_scope_id = left_handle.id
            left_view = self.render_scope_with_handle(left_handle, self._build_left)
        with self.scope("right_counter") as right_handle:
            self._right_scope_id = right_handle.id
            right_view = self.render_scope_with_handle(right_handle, self._build_right)

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
            [left_view, right_view, controls],
            padding=12,
            gap=16,
            cross_alignment="center",
        )

    def _build_left(self) -> Widget:
        return Text(f"Left scope value: {self.left_value}")

    def _build_right(self) -> Widget:
        return Text(f"Right scope value: {self.right_value}")

    def _increment_left(self) -> None:
        self.left_value += 1
        if self._left_scope_id:
            self.invalidate_scope_id(self._left_scope_id)

    def _increment_right(self) -> None:
        self.right_value += 1
        if self._right_scope_id:
            self.invalidate_scope_id(self._right_scope_id)

    def _reset(self) -> None:
        self.left_value = 0
        self.right_value = 0
        if self._left_scope_id:
            self.invalidate_scope_id(self._left_scope_id)
        if self._right_scope_id:
            self.invalidate_scope_id(self._right_scope_id)


if __name__ == "__main__":
    demo = ScopeCounterDemo()
    app = MaterialApp(content=demo)
    app.run()
