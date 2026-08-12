"""Observable: Patterns and Recipes

Demonstrates:
- ViewModel pattern (state/logic separation from rendering)
- Derived state composition with map() and combine()
- Memory management with Disposable

Work produced on a worker thread lives in background_work.py.
"""

import nuiitivet.material as nv

# ---------------------------------------------------------------------------
# Pattern 1: ViewModel
# ---------------------------------------------------------------------------


class TodoViewModel:
    """Owns all state and business logic. The View only reads and forwards."""

    items: nv.Observable[list[str]] = nv.Observable([])
    selected_index: nv.Observable[int | None] = nv.Observable(None)

    def __init__(self) -> None:
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
# Combined demo widget
# ---------------------------------------------------------------------------


class PatternsApp(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.vm = TodoViewModel()
        self.cart = ShoppingCart()
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
