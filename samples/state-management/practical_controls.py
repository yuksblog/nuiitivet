"""Observable: Practical Controls

Demonstrates:
- batch() to group updates and suppress intermediate notifications
- debounce() to fire only after input has settled
- throttle() to sample high-frequency events at a fixed rate
- Chaining operators (debounce → map)
"""

import nuiitivet.material as nv


class BatchModel:
    """Two source observables with a computed total.

    With batch(), the subscriber fires only once per group of updates
    instead of twice.
    """

    def __init__(self) -> None:
        self.price = nv.Observable(100)
        self.quantity = nv.Observable(2)
        self.notify_count = nv.Observable(0)

        self.total = self.price.combine(self.quantity).compute(lambda p, q: p * q)
        self.total.subscribe(lambda _: self.notify_count.set(self.notify_count.value + 1))

    def update_batched(self) -> None:
        """Update both observables atomically → one notification."""
        with nv.batch():
            self.price.value += 10
            self.quantity.value += 1

    def update_unbatched(self) -> None:
        """Update both without batch → two notifications."""
        self.price.value += 10
        self.quantity.value += 1


class DebounceModel:
    """Debounce: fire only after input settles for 0.5 s."""

    def __init__(self) -> None:
        self.raw_count = nv.Observable(0)
        self.execute_count = nv.Observable(0)

        # Named -> held. One window, two consumers below. A derived Observable
        # nobody holds is collected and never fires.
        self.debounced = self.raw_count.debounce(0.5)

        # Chained and bound straight into the UI. The map() is required for now:
        # the wrapper's own .value reads through to the live source, so binding
        # it directly would not be debounced at all. #557 makes wrappers hold
        # their own value; the map() becomes optional then.
        self.settled = self.debounced.map(lambda n: f"Settled at: {n} clicks")

        # subscribe() because counting *emissions* is accumulation over history,
        # which map()/compute() cannot express - they recompute from the current
        # value. There is no handler to hold an imperative counter either: the
        # thing being counted is an operator's output, not a user action.
        self._subscription = self.debounced.subscribe(
            lambda _: self.execute_count.set(self.execute_count.value + 1)
        )

    def click(self) -> None:
        self.raw_count.value += 1


class ThrottleModel:
    """Throttle: fire at most once every 0.5 s."""

    def __init__(self) -> None:
        self.raw_count = nv.Observable(0)
        self.execute_count = nv.Observable(0)

        # Same shape as DebounceModel: name the window, then derive from it.
        self.throttled = self.raw_count.throttle(0.5)
        self.sampled = self.throttled.map(lambda n: f"Sampled at: {n} clicks")
        self._subscription = self.throttled.subscribe(
            lambda _: self.execute_count.set(self.execute_count.value + 1)
        )

    def click(self) -> None:
        self.raw_count.value += 1


class PracticalControlsApp(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.batch_model = BatchModel()
        self.debounce_model = DebounceModel()
        self.throttle_model = ThrottleModel()

    def build(self) -> nv.Widget:
        bm = self.batch_model
        dm = self.debounce_model
        tm = self.throttle_model

        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=20,
                children=[
                    # --- batch() ---
                    nv.Text("batch()"),
                    nv.Text(bm.price.map(lambda p: f"Price: {p}")),
                    nv.Text(bm.quantity.map(lambda q: f"Quantity: {q}")),
                    nv.Text(bm.total.map(lambda t: f"Total: {t}")),
                    nv.Text(bm.notify_count.map(lambda n: f"Subscriber fired: {n}x")),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button(
                                "Update (batched)",
                                on_click=lambda: bm.update_batched(),
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Button(
                                "Update (unbatched)",
                                on_click=lambda: bm.update_unbatched(),
                                style=nv.ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                    # --- debounce() ---
                    nv.Text("debounce(0.5 s)"),
                    nv.Text(dm.raw_count.map(lambda n: f"Clicks: {n}")),
                    nv.Text(dm.settled),  # debounce -> map, bound directly
                    nv.Text(dm.execute_count.map(lambda n: f"Executed: {n}x")),
                    nv.Button(
                        "Click (debounced)",
                        on_click=lambda: dm.click(),
                        style=nv.ButtonStyle.filled(),
                    ),
                    # --- throttle() ---
                    nv.Text("throttle(0.5 s)"),
                    nv.Text(tm.raw_count.map(lambda n: f"Clicks: {n}")),
                    nv.Text(tm.sampled),  # throttle -> map, bound directly
                    nv.Text(tm.execute_count.map(lambda n: f"Executed: {n}x")),
                    nv.Button(
                        "Click (throttled)",
                        on_click=lambda: tm.click(),
                        style=nv.ButtonStyle.filled(),
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = PracticalControlsApp()
    app = nv.App(content=widget)
    try:
        app.run()
    except Exception:
        print("Practical Controls demo requires pyglet/skia to run.")
