"""TODO List Sample - Observable Phase 1

Demonstrates:
- Observable.compute() for complex derived state
- Dynamic dependency tracking
- Conditional logic in computed observables
- List management with observables
"""

from typing import List
from dataclasses import dataclass

from nuiitivet.observable import Observable
from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.material import Checkbox
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import FilledButton, OutlinedButton
from nuiitivet.widgets.box import Box


@dataclass
class TodoItem:
    """A single TODO item"""

    id: int
    text: str
    completed: bool = False


class TodoViewModel:
    """TODO list with computed statistics"""

    # Define observables as class attributes (descriptors)
    items: Observable[List[TodoItem]] = Observable([])
    filter_mode = Observable("all")  # "all", "active", "completed"

    def __init__(self):
        self._next_id = 1

        # Computed: filtered items based on mode
        self.filtered_items = Observable.compute(
            lambda: [
                item
                for item in self.items.value
                if self.filter_mode.value == "all"
                or (self.filter_mode.value == "active" and not item.completed)
                or (self.filter_mode.value == "completed" and item.completed)
            ]
        )

        # Computed: statistics using Observable.compute()
        self.total_count = self.items.map(lambda items: len(items))

        self.completed_count = Observable.compute(lambda: sum(1 for item in self.items.value if item.completed))

        self.active_count = Observable.compute(lambda: sum(1 for item in self.items.value if not item.completed))

        # Computed: summary with conditional logic
        self.summary = Observable.compute(
            lambda: (
                f"Total: {self.total_count.value} | "
                f"Completed: {self.completed_count.value} | "
                f"Active: {self.active_count.value}"
                if self.total_count.value > 0
                else "No tasks"
            )
        )

        # Computed: filter label
        self.filter_label = self.filter_mode.map(
            lambda mode: {"all": "All", "active": "Active", "completed": "Completed"}[mode]
        )

        # Computed: filter display
        self.filter_display = self.filter_label.map(lambda label: f"Filter: {label}")

        # Computed: clear button text
        self.clear_button_text = self.completed_count.map(lambda count: f"Clear Completed ({count})")

    def add_item(self, text: str):
        """Add a new TODO item"""
        if text.strip():
            new_item = TodoItem(id=self._next_id, text=text.strip())
            self._next_id += 1
            self.items.value = self.items.value + [new_item]

    def toggle_item(self, item_id: int):
        """Toggle completion status"""
        items = [
            TodoItem(id=item.id, text=item.text, completed=not item.completed) if item.id == item_id else item
            for item in self.items.value
        ]
        self.items.value = items

    def remove_item(self, item_id: int):
        """Remove a TODO item"""
        self.items.value = [item for item in self.items.value if item.id != item_id]

    def clear_completed(self):
        """Remove all completed items"""
        self.items.value = [item for item in self.items.value if not item.completed]

    def set_filter(self, mode: str):
        """Change filter mode"""
        self.filter_mode.value = mode


class TodoApp(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.viewmodel = TodoViewModel()

        # Add some sample items
        self.viewmodel.add_item("Implement Phase 1 features")
        self.viewmodel.add_item("Create sample applications")
        self.viewmodel.add_item("Update documentation")

    def build(self) -> Widget:
        vm = self.viewmodel

        return Column(
            padding=20,
            gap=20,
            main_alignment="start",
            children=[
                # Title
                Text(
                    "TODO List",
                ),
                # Description
                Text(
                    "Dynamic statistics with Observable.compute()",
                    style=TextStyle(color=(100, 100, 100, 255)),
                ),
                # Add button
                Row(
                    gap=10,
                    children=[
                        FilledButton(
                            "Add New Task", on_click=lambda: vm.add_item(f"New task {vm.total_count.value + 1}")
                        ),
                    ],
                ),
                # Statistics
                Box(
                    padding=15,
                    background_color=(240, 255, 240, 255),
                    child=Column(
                        gap=5,
                        children=[
                            Text("Statistics"),
                            Text(vm.summary),
                        ],
                    ),
                ),
                # Filter buttons
                Column(
                    gap=8,
                    children=[
                        Text(vm.filter_display),
                        Row(
                            gap=10,
                            children=[
                                FilledButton("All", on_click=lambda: vm.set_filter("all")),
                                FilledButton("Active", on_click=lambda: vm.set_filter("active")),
                                FilledButton("Completed", on_click=lambda: vm.set_filter("completed")),
                            ],
                        ),
                    ],
                ),
                # TODO items list
                ForEach(
                    vm.filtered_items,
                    builder=lambda item, idx: self._build_todo_item(item),
                    key=lambda item, idx: item.id,
                ),
                # Clear completed button
                OutlinedButton(
                    vm.clear_button_text,
                    on_click=lambda: vm.clear_completed(),
                ),
            ],
        )

    def _build_todo_item(self, item: TodoItem) -> Widget:
        """Build a single TODO item widget"""
        vm = self.viewmodel

        return Box(
            padding=10,
            background_color=(255, 255, 255, 255) if not item.completed else (245, 245, 245, 255),
            child=Row(
                gap=10,
                children=[
                    Checkbox(
                        checked=item.completed,
                        on_toggle=lambda checked: vm.toggle_item(item.id),
                    ),
                    Text(
                        item.text,
                        style=TextStyle(color=((100, 100, 100, 255) if item.completed else (0, 0, 0, 255))),
                    ),
                    OutlinedButton("Delete", on_click=lambda: vm.remove_item(item.id)),
                ],
            ),
        )


if __name__ == "__main__":
    widget = TodoApp()
    app = MaterialApp(content=widget)
    try:
        app.run()
    except Exception:
        print("TODO demo requires pyglet/skia to run.")
