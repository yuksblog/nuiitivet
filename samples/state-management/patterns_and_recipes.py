"""Observable: Patterns and Recipes

Demonstrates:
- ViewModel pattern (state/logic separation from rendering)
- Derived state composition with map() and combine()
- Memory management with Disposable
- Typed values derived from a text field's text
- A busy flag held with while_value() while an async handler runs

Work produced on a worker thread lives in background_work.py.
"""

import asyncio
from datetime import date

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
# Pattern 4: Typed values from text input
# ---------------------------------------------------------------------------

# Dates the room is already taken. A parseable date can still be unacceptable,
# which is why the application decides what counts as an error, not the widget.
BOOKED = {date(2026, 7, 4), date(2026, 7, 5)}


def to_int(text: str) -> int | None:
    """Read the text as an integer, tolerating what a paste brings with it.

    ``int()`` strips whitespace itself, including the U+00A0 that copying from a
    web page produces; a ``str.isdigit()`` test would reject all of those.
    """
    try:
        return int(text)
    except ValueError:
        return None


def arrival_error(text: str) -> str | None:
    """What is wrong with this text, if anything -- the whole decision, once."""
    if not text:
        return None
    arrival = nv.parse_date(text)
    if arrival is None:
        return "Invalid date"
    if arrival in BOOKED:
        return "Already booked"
    return None


class OrderForm:
    """The field writes into the text; everything else is derived from it.

    ``qty`` converts every value the text takes, reporting None when it cannot.
    ``qty_held`` passes only values the predicate accepts, so one it refuses
    leaves the previous result standing -- an empty field included.
    """

    def __init__(self) -> None:
        self.qty_text = nv.Observable("1")
        self.qty = self.qty_text.map(to_int)
        self.qty_held = self.qty_text.filter(str.isdigit, initial="1").map(int)

        self.arrival_text = nv.Observable("")
        self.arrival = self.arrival_text.map(nv.parse_date)
        # One decision, two presentations of it: deriving is_error and
        # supporting_text from the text separately would write it twice.
        self.error = self.arrival_text.map(arrival_error)


# ---------------------------------------------------------------------------
# Pattern 5: Busy flag while an async handler runs
# ---------------------------------------------------------------------------


class SaveViewModel:
    """``busy`` is True exactly while ``save()`` runs, however it exits."""

    def __init__(self) -> None:
        self.busy = nv.Observable(False)
        self.saved_count = nv.Observable(0)

    async def save(self) -> None:
        async with self.busy.while_value(True):
            await asyncio.sleep(1.0)  # stands in for the real I/O
            self.saved_count.value += 1


# ---------------------------------------------------------------------------
# Combined demo widget
# ---------------------------------------------------------------------------


class PatternsApp(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.vm = TodoViewModel()
        self.cart = ShoppingCart()
        self.form = OrderForm()
        self.save_vm = SaveViewModel()
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
        form = self.form

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
                    # --- Typed values from text input ---
                    nv.Text("Pattern 4: Typed Values from Text Input"),
                    nv.TextField(
                        value=form.qty_text,
                        label="Quantity",
                        # Runs on paste too, so "1,234" lands as "1234".
                        input_filter=nv.digits_only(),
                        width=320,
                        style=nv.TextFieldStyle.outlined(),
                    ),
                    nv.Text(form.qty.map(lambda n: f"map():           {n}")),
                    nv.Text(form.qty_held.map(lambda n: f"filter().map():  {n}")),
                    nv.DockedDatePicker(
                        value=form.arrival_text,
                        label="Arrival",
                        supporting_text=form.error,
                        is_error=form.error.map(lambda e: e is not None),
                    ),
                    nv.Text(form.arrival.map(lambda d: f"arrival:         {d}")),
                    # --- Busy flag while an async handler runs ---
                    nv.Text("Pattern 5: Busy Flag While a Handler Runs"),
                    nv.Row(
                        gap=8,
                        children=[
                            nv.Button(
                                "Save",
                                on_click=self.save_vm.save,
                                disabled=self.save_vm.busy,
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Text(self.save_vm.saved_count.map(lambda n: f"saved {n} time(s)")),
                        ],
                    ),
                ],
            ),
        )


def main() -> None:
    # The class, not an instance: hot reload rebuilds the root by calling it.
    nv.App(nv.Window(content=PatternsApp, title="Observable: Patterns and Recipes", width=560, height=980)).run()


if __name__ == "__main__":
    main()
