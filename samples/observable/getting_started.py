"""Observable: Getting Started

Demonstrates:
- Basic Observable usage (instance attribute style)
- Derived state with .map()
- Observable as a class attribute (descriptor pattern)
- Integration with UI widgets
"""

from nuiitivet.observable import Observable
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Text, ButtonStyle
from nuiitivet.material.buttons import Button
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box

# --- Basic Usage: instance attribute style ---


class Counter:
    """Simple counter with a derived double_count."""

    def __init__(self) -> None:
        self.count = Observable(0)
        self.double_count = self.count.map(lambda c: c * 2)

    def increment(self) -> None:
        self.count.value += 1

    def decrement(self) -> None:
        if self.count.value > 0:
            self.count.value -= 1


# --- Class Attribute (descriptor) style ---


class Model:
    """Class-level Observable descriptor with per-instance state.

    ``value`` is defined once as a class attribute, so every instance shares the
    same descriptor object. Each instance nonetheless holds its *own* value
    (stored on the instance), so mutating one instance's ``value`` never affects
    another's.
    """

    value: Observable[int] = Observable(0)


# --- UI Integration ---


class CounterApp(ComposableWidget):
    """Counter demo that wires Observable state into the widget tree."""

    def __init__(self) -> None:
        super().__init__()
        self.counter = Counter()

        # Derived label updated automatically
        self.label = self.counter.count.map(lambda c: f"Count: {c}")
        self.double_label = self.counter.double_count.map(lambda d: f"Double: {d}")

    def build(self) -> Widget:
        return Box(
            padding=24,
            child=Column(
                gap=16,
                children=[
                    Text("Observable: Getting Started"),
                    Text(self.label),
                    Text(self.double_label),
                    Row(
                        gap=12,
                        children=[
                            Button(
                                "Increment",
                                on_click=lambda: self.counter.increment(),
                                style=ButtonStyle.filled(),
                            ),
                            Button(
                                "Decrement",
                                on_click=lambda: self.counter.decrement(),
                                style=ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = CounterApp()
    app = App(content=widget)
    try:
        app.run()
    except Exception:
        print("Getting started demo requires pyglet/skia to run.")
