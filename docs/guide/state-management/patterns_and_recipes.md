# Observable: Patterns and Recipes

## ViewModel Pattern

Keep source state and derived state in a ViewModel, and keep rendering logic in the View.

This pattern makes responsibilities clear:

- The ViewModel owns state transitions and business logic.
- The View only renders and forwards user actions.
- Derived values (such as counts and flags) are centralized and reusable.

As a result, code becomes easier to test, reason about, and maintain.

```python
import nuiitivet.material as nv

class TodoViewModel:
    items = nv.Observable([])
    selected_item = nv.Observable(None)

    def __init__(self):
        self.items.dispatch_to_ui()
        self.selected_item.dispatch_to_ui()
        self.item_count = self.items.map(lambda items: len(items))
        self.has_items = self.item_count.map(lambda count: count > 0)

    def add_item(self, text: str):
        with nv.batch():
            current = self.items.value
            self.items.value = current + [{"text": text, "done": False}]
```

In this structure, the View does not mutate low-level state directly.
It only invokes ViewModel methods, while rendering uses Observable-derived values.

```python
import nuiitivet.material as nv

class TodoView:
    def __init__(self, vm: TodoViewModel):
        self.vm = vm

    def build(self):
        return nv.Column(
            children=[
                nv.Text(text=self.vm.item_count.map(lambda c: f"Items: {c}")),
                nv.Button(
                    text="Add",
                    on_click=lambda: self.vm.add_item("New item")
                , style=nv.ButtonStyle.filled()),
            ]
        )
```

## Derived State Composition

Use derived state composition when one value should be computed from other observables.
This keeps calculation logic in one place and avoids duplicating the same formula across multiple views.
It also makes changes safer because you only update the derivation once.

```python
import nuiitivet.material as nv

class ShoppingCart:
    items = nv.Observable([])
    tax_rate = nv.Observable(0.1)

    def __init__(self):
        self.subtotal = self.items.map(
            lambda items: sum(item["price"] * item["qty"] for item in items)
        )
        self.total = nv.combine(self.subtotal, self.tax_rate).compute(
            lambda sub, rate: sub * (1 + rate)
        )
```

## Async Data Fetch Recipe

Use this pattern when data is loaded on a worker thread but rendered in the UI.
The key point is to keep UI-facing observables dispatched to the UI thread while tracking loading and error state explicitly.
This gives you predictable rendering for success, loading, and failure paths.

```python
import threading
import nuiitivet.material as nv

class DataViewModel:
    data = nv.Observable([])
    loading = nv.Observable(False)
    error = nv.Observable(None)

    def __init__(self):
        self.data.dispatch_to_ui()
        self.loading.dispatch_to_ui()
        self.error.dispatch_to_ui()

    def load_data_async(self):
        def worker():
            try:
                self.loading.value = True
                self.error.value = None
                result = fetch_data_from_api()
                self.data.value = result
            except Exception as e:
                self.error.value = str(e)
            finally:
                self.loading.value = False

        threading.Thread(target=worker).start()
```

---

## Next Steps

- [State Management Overview](index.md)
- [Async & Threading Guide](../advanced/threading.md)
