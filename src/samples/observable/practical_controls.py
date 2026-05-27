"""Observable: Practical Controls

Demonstrates:
- batch() to group updates and suppress intermediate notifications
- debounce() to fire only after input has settled
- throttle() to sample high-frequency events at a fixed rate
- Chaining operators (debounce → map → dispatch_to_ui)
"""

from nuiitivet.observable import Observable, batch
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Text, ButtonStyle
from nuiitivet.material.buttons import Button
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box


class BatchModel:
    """Two source observables with a computed total.

    With batch(), the subscriber fires only once per group of updates
    instead of twice.
    """

    def __init__(self) -> None:
        self.price = Observable(100)
        self.quantity = Observable(2)
        self.notify_count = Observable(0)

        self.total = self.price.combine(self.quantity).compute(lambda p, q: p * q)
        self.total.subscribe(lambda _: setattr(self.notify_count, "value", self.notify_count.value + 1))

    def update_batched(self) -> None:
        """Update both observables atomically → one notification."""
        with batch():
            self.price.value += 10
            self.quantity.value += 1

    def update_unbatched(self) -> None:
        """Update both without batch → two notifications."""
        self.price.value += 10
        self.quantity.value += 1


class DebounceModel:
    """Debounce: fire only after input settles for 0.5 s."""

    def __init__(self) -> None:
        self.raw_count = Observable(0)
        self.execute_count = Observable(0)

        debounced = self.raw_count.debounce(0.5)
        debounced.subscribe(lambda _: setattr(self.execute_count, "value", self.execute_count.value + 1))

    def click(self) -> None:
        self.raw_count.value += 1


class ThrottleModel:
    """Throttle: fire at most once every 0.5 s."""

    def __init__(self) -> None:
        self.raw_count = Observable(0)
        self.execute_count = Observable(0)

        throttled = self.raw_count.throttle(0.5)
        throttled.subscribe(lambda _: setattr(self.execute_count, "value", self.execute_count.value + 1))

    def click(self) -> None:
        self.raw_count.value += 1


class PracticalControlsApp(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.batch_model = BatchModel()
        self.debounce_model = DebounceModel()
        self.throttle_model = ThrottleModel()

    def build(self) -> Widget:
        bm = self.batch_model
        dm = self.debounce_model
        tm = self.throttle_model

        return Box(
            padding=24,
            child=Column(
                gap=20,
                children=[
                    # --- batch() ---
                    Text("batch()"),
                    Text(bm.price.map(lambda p: f"Price: {p}")),
                    Text(bm.quantity.map(lambda q: f"Quantity: {q}")),
                    Text(bm.total.map(lambda t: f"Total: {t}")),
                    Text(bm.notify_count.map(lambda n: f"Subscriber fired: {n}x")),
                    Row(
                        gap=12,
                        children=[
                            Button(
                                "Update (batched)",
                                on_click=lambda: bm.update_batched(),
                                style=ButtonStyle.filled(),
                            ),
                            Button(
                                "Update (unbatched)",
                                on_click=lambda: bm.update_unbatched(),
                                style=ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                    # --- debounce() ---
                    Text("debounce(0.5 s)"),
                    Text(dm.raw_count.map(lambda n: f"Clicks: {n}")),
                    Text(dm.execute_count.map(lambda n: f"Executed: {n}x")),
                    Button(
                        "Click (debounced)",
                        on_click=lambda: dm.click(),
                        style=ButtonStyle.filled(),
                    ),
                    # --- throttle() ---
                    Text("throttle(0.5 s)"),
                    Text(tm.raw_count.map(lambda n: f"Clicks: {n}")),
                    Text(tm.execute_count.map(lambda n: f"Executed: {n}x")),
                    Button(
                        "Click (throttled)",
                        on_click=lambda: tm.click(),
                        style=ButtonStyle.filled(),
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = PracticalControlsApp()
    app = App(content=widget)
    try:
        app.run()
    except Exception:
        print("Practical Controls demo requires pyglet/skia to run.")
