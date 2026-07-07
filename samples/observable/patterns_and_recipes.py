"""Observable: Patterns and Recipes

Demonstrates:
- ViewModel pattern (state/logic separation from rendering)
- Derived state composition with map() and combine()
- Memory management with Disposable
- Async data fetch recipe using dispatch_to_ui()
"""

import threading
import time

import nuiitivet.material as nv

# ---------------------------------------------------------------------------
# Pattern 1: ViewModel
# ---------------------------------------------------------------------------


class TodoViewModel:
    """Owns all state and business logic. The View only reads and forwards."""

    items: nv.Observable[list[str]] = nv.Observable([])
    selected_index: nv.Observable[int | None] = nv.Observable(None)

    def __init__(self) -> None:
        self.items.dispatch_to_ui()
        self.selected_index.dispatch_to_ui()

        self.item_count = self.items.map(lambda lst: len(lst))
        self.has_items = self.item_count.map(lambda c: c > 0)
        self.summary = self.item_count.map(lambda c: f"{c} item(s)" if c > 0 else "No items")

    def add_item(self, text: str) -> None:
        with nv.batch():
            self.items.value = self.items.value + [text]

    def remove_selected(self) -> None:
        idx = self.selected_index.value
        if idx is not None and 0 <= idx < len(self.items.value):
            lst = list(self.items.value)
            lst.pop(idx)
            with nv.batch():
                self.items.value = lst
                self.selected_index.value = None

    def select(self, idx: int) -> None:
        self.selected_index.value = idx


# ---------------------------------------------------------------------------
# Pattern 2: Derived State Composition
# ---------------------------------------------------------------------------


class ShoppingCart:
    """Subtotal and total derived from items + tax_rate."""

    items: nv.Observable[list[dict]] = nv.Observable([])
    tax_rate: nv.Observable[float] = nv.Observable(0.1)

    def __init__(self) -> None:
        self.subtotal = self.items.map(lambda lst: sum(item["price"] * item["qty"] for item in lst))
        self.total = nv.combine(self.subtotal, self.tax_rate).compute(lambda sub, rate: int(sub * (1 + rate)))

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
        self.count = nv.Observable(0)
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

    data: nv.Observable[str] = nv.Observable("")
    loading: nv.Observable[bool] = nv.Observable(False)
    error: nv.Observable[str | None] = nv.Observable(None)

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


class PatternsApp(nv.ComposableWidget):
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

    def build(self) -> nv.Widget:
        vm = self.vm
        cart = self.cart
        avm = self.async_vm

        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=20,
                children=[
                    # --- ViewModel pattern ---
                    nv.Text("Pattern 1: ViewModel"),
                    nv.Text(vm.summary),
                    nv.Row(
                        gap=8,
                        children=[
                            nv.Button(
                                "Add item",
                                on_click=lambda: self._add_todo_item(),
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Button(
                                "Remove first",
                                on_click=lambda: self._remove_first(),
                                style=nv.ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                    # --- Derived state composition ---
                    nv.Text("Pattern 2: Derived State Composition"),
                    nv.Text(cart.subtotal.map(lambda s: f"Subtotal: ¥{s:,}")),
                    nv.Text(cart.total.map(lambda t: f"Total (w/ tax): ¥{t:,}")),
                    nv.Row(
                        gap=8,
                        children=[
                            nv.Button(
                                "Add ¥500 item",
                                on_click=lambda: cart.add_item(500, 1),
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Button(
                                "Clear cart",
                                on_click=lambda: cart.clear(),
                                style=nv.ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                    # --- Async fetch ---
                    nv.Text("Pattern 4: Async Data Fetch"),
                    nv.Text(avm.status),
                    nv.Text(avm.data_display),
                    nv.Text(avm.error_display),
                    nv.Button(
                        "Fetch data",
                        on_click=lambda: avm.fetch(),
                        style=nv.ButtonStyle.filled(),
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = PatternsApp()
    app = nv.App(content=widget)
    try:
        app.run()
    except Exception:
        print("Patterns and Recipes demo requires pyglet/skia to run.")
