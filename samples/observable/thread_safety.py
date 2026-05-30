"""Observable: Thread Safety

Demonstrates:
- .dispatch_to_ui() to route notifications to the UI thread
- Async data loading from a worker thread
- Loading / error / success state pattern
- Operator chaining with dispatch_to_ui() at the end of the chain
"""

import threading
import time

from nuiitivet.observable import Observable
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Text, ButtonStyle
from nuiitivet.material.buttons import Button
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box


class AsyncLoaderViewModel:
    """Fetches data on a worker thread; observables are dispatched to the UI thread."""

    data: Observable[str | None] = Observable(None)
    loading: Observable[bool] = Observable(False)
    error: Observable[str | None] = Observable(None)

    def __init__(self) -> None:
        # All three observables that touch UI must be dispatched to the UI thread
        self.data.dispatch_to_ui()
        self.loading.dispatch_to_ui()
        self.error.dispatch_to_ui()

        # Derived values built on top of dispatched observables
        self.status_text = self.loading.map(lambda loading: "⏳ Loading…" if loading else "")
        self.data_text = self.data.map(lambda d: d if d is not None else "(no data loaded yet)")
        self.error_text = self.error.map(lambda e: f"⚠ {e}" if e else "")

        # Chaining example: derive display from data, then dispatch to UI
        self.data_upper = self.data.map(lambda d: d.upper() if d else "").dispatch_to_ui()

    def fetch(self, should_fail: bool = False) -> None:
        """Spawn a worker thread that updates observables safely."""

        def worker() -> None:
            try:
                self.loading.value = True
                self.error.value = None
                self.data.value = None

                time.sleep(1.2)  # Simulate network latency

                if should_fail:
                    raise RuntimeError("Simulated network error")

                self.data.value = f"Result fetched at {time.strftime('%H:%M:%S')}"

            except Exception as exc:
                self.error.value = str(exc)
            finally:
                self.loading.value = False

        threading.Thread(target=worker, daemon=True).start()


class ThreadSafetyApp(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.vm = AsyncLoaderViewModel()

    def build(self) -> Widget:
        vm = self.vm
        return Box(
            padding=24,
            child=Column(
                gap=16,
                children=[
                    Text("Observable: Thread Safety"),
                    Text("Workers update observables from a background thread."),
                    Text("dispatch_to_ui() ensures callbacks run on the UI thread."),
                    Text(vm.status_text),
                    Text(vm.data_text),
                    Text(vm.data_upper),
                    Text(vm.error_text),
                    Row(
                        gap=12,
                        children=[
                            Button(
                                "Fetch (success)",
                                on_click=lambda: vm.fetch(should_fail=False),
                                style=ButtonStyle.filled(),
                            ),
                            Button(
                                "Fetch (error)",
                                on_click=lambda: vm.fetch(should_fail=True),
                                style=ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = ThreadSafetyApp()
    app = App(content=widget)
    try:
        app.run()
    except Exception:
        print("Thread Safety demo requires pyglet/skia to run.")
