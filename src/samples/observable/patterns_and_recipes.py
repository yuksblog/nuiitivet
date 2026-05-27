"""Observable: Patterns and Recipes

Demonstrates:
- ViewModel pattern (state/logic separation from rendering)
- Derived state composition with map() and combine()
- Memory management with Disposable
- Async data fetch recipe using dispatch_to_ui()
"""

import threading
import time

from nuiitivet.observable import Observable, combine, batch
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Text, ButtonStyle
from nuiitivet.material.buttons import Button
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box

# ---------------------------------------------------------------------------
# Pattern 1: ViewModel
# ---------------------------------------------------------------------------


class TodoViewModel:
    """Owns all state and business logic. The View only reads and forwards."""

    items: Observable[list[str]] = Observable([])
    selected_index: Observable[int | None] = Observable(None)

    def __init__(self) -> None:
        self.items.dispatch_to_ui()
        self.selected_index.dispatch_to_ui()

        self.item_count = self.items.map(lambda lst: len(lst))
        self.has_items = self.item_count.map(lambda c: c > 0)
        self.summary = self.item_count.map(lambda c: f"{c} item(s)" if c > 0 else "No items")

    def add_item(self, text: str) -> None:
        with batch():
            self.items.value = self.items.value + [text]

    def remove_selected(self) -> None:
        idx = self.selected_index.value
        if idx is not None and 0 <= idx < len(self.items.value):
            lst = list(self.items.value)
            lst.pop(idx)
            with batch():
                self.items.value = lst
                self.selected_index.value = None

    def select(self, idx: int) -> None:
        self.selected_index.value = idx


# ---------------------------------------------------------------------------
# Pattern 2: Derived State Composition
# ---------------------------------------------------------------------------


class ShoppingCart:
    """Subtotal and total derived from items + tax_rate."""

    items: Observable[list[dict]] = Observable([])
    tax_rate: Observable[float] = Observable(0.1)

    def __init__(self) -> None:
        self.subtotal = self.items.map(lambda lst: sum(item["price"] * item["qty"] for item in lst))
        self.total = combine(self.subtotal, self.tax_rate).compute(lambda sub, rate: int(sub * (1 + rate)))

    def add_item(self, price: int, qty: int) -> None:
        self.items.value = self.items.value + [{"price": price, "qty": qty}]

    def clear(self) -> None:
        self.items.value = []


# ---------------------------------------------------------------------------
# Pattern 3: Manual lifecycle management
# ---------------------------------------------------------------------------


class ManagedViewModel:
    """Holds derived observables and releases them on dispose()."""

    def __init__(self) -> None:
        self.count = Observable(0)
        self.doubled = self.count.map(lambda x: x * 2)
        # Keep explicit reference so GC does not collect the derived observable
        self._disposables = [self.doubled]

    def increment(self) -> None:
        self.count.value += 1

    def dispose(self) -> None:
        for d in self._disposables:
            d.dispose()
        self._disposables.clear()


# ---------------------------------------------------------------------------
# Pattern 4: Async data fetch recipe
# ---------------------------------------------------------------------------


class AsyncViewModel:
    """Thread-safe async fetch using dispatch_to_ui()."""

    data: Observable[str] = Observable("")
    loading: Observable[bool] = Observable(False)
    error: Observable[str | None] = Observable(None)

    def __init__(self) -> None:
        self.data.dispatch_to_ui()
        self.loading.dispatch_to_ui()
        self.error.dispatch_to_ui()

        self.status = self.loading.map(lambda loading: "Loading..." if loading else "")
        self.data_display = self.data.map(lambda d: d if d else "(no data)")
        self.error_display = self.error.map(lambda e: f"Error: {e}" if e else "")

    def fetch(self) -> None:
        def worker() -> None:
            try:
                self.loading.value = True
                self.error.value = None
                time.sleep(1.0)  # Simulate network latency
                self.data.value = f"Fetched at {time.strftime('%H:%M:%S')}"
            except Exception as exc:
                self.error.value = str(exc)
            finally:
                self.loading.value = False

        threading.Thread(target=worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Combined demo widget
# ---------------------------------------------------------------------------


class PatternsApp(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.vm = TodoViewModel()
        self.cart = ShoppingCart()
        self.async_vm = AsyncViewModel()
        self._counter = 1

    def _add_todo_item(self) -> None:
        self.vm.add_item(f"Task {self._counter}")
        self._counter += 1

    def _remove_first(self) -> None:
        self.vm.select(0)
        self.vm.remove_selected()

    def build(self) -> Widget:
        vm = self.vm
        cart = self.cart
        avm = self.async_vm

        return Box(
            padding=24,
            child=Column(
                gap=20,
                children=[
                    # --- ViewModel pattern ---
                    Text("Pattern 1: ViewModel"),
                    Text(vm.summary),
                    Row(
                        gap=8,
                        children=[
                            Button(
                                "Add item",
                                on_click=lambda: self._add_todo_item(),
                                style=ButtonStyle.filled(),
                            ),
                            Button(
                                "Remove first",
                                on_click=lambda: self._remove_first(),
                                style=ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                    # --- Derived state composition ---
                    Text("Pattern 2: Derived State Composition"),
                    Text(cart.subtotal.map(lambda s: f"Subtotal: ¥{s:,}")),
                    Text(cart.total.map(lambda t: f"Total (w/ tax): ¥{t:,}")),
                    Row(
                        gap=8,
                        children=[
                            Button(
                                "Add ¥500 item",
                                on_click=lambda: cart.add_item(500, 1),
                                style=ButtonStyle.filled(),
                            ),
                            Button(
                                "Clear cart",
                                on_click=lambda: cart.clear(),
                                style=ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                    # --- Async fetch ---
                    Text("Pattern 4: Async Data Fetch"),
                    Text(avm.status),
                    Text(avm.data_display),
                    Text(avm.error_display),
                    Button(
                        "Fetch data",
                        on_click=lambda: avm.fetch(),
                        style=ButtonStyle.filled(),
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = PatternsApp()
    app = App(content=widget)
    try:
        app.run()
    except Exception:
        print("Patterns and Recipes demo requires pyglet/skia to run.")
