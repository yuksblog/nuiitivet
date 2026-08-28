"""Observable: Getting Started

Demonstrates:
- Basic Observable usage (instance attribute style)
- Derived state with .map()
- Observable as a class attribute (descriptor pattern)
- Integration with UI widgets
"""

import nuiitivet.material as nv

# --- Basic Usage: instance attribute style ---


class Counter:
    """Simple counter with a derived double_count."""

    def __init__(self) -> None:
        self.count = nv.Observable(0)
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

    value: nv.Observable[int] = nv.Observable(0)


# --- UI Integration ---


class CounterApp(nv.ComposableWidget):
    """Counter demo that wires Observable state into the widget tree."""

    def __init__(self) -> None:
        super().__init__()
        self.counter = Counter()

        # Derived label updated automatically
        self.label = self.counter.count.map(lambda c: f"Count: {c}")
        self.double_label = self.counter.double_count.map(lambda d: f"Double: {d}")

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Observable: Getting Started"),
                    nv.Text(self.label),
                    nv.Text(self.double_label),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button(
                                "Increment",
                                on_click=lambda: self.counter.increment(),
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Button(
                                "Decrement",
                                on_click=lambda: self.counter.decrement(),
                                style=nv.ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = CounterApp()
    app = nv.App(nv.Window(content=widget))
    try:
        app.run()
    except Exception:
        print("Getting started demo requires pyglet/skia to run.")
