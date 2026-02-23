---
layout: default
---

# Observable: Patterns and Recipes

## ViewModel Pattern

Keep source state and derived state in a ViewModel, and keep rendering logic in the View.

This pattern makes responsibilities clear:

- The ViewModel owns state transitions and business logic.
- The View only renders and forwards user actions.
- Derived values (such as counts and flags) are centralized and reusable.

As a result, code becomes easier to test, reason about, and maintain.

```python
from nuiitivet.observable import Observable, batch

class TodoViewModel:
    items = Observable([])
    selected_item = Observable(None)

    def __init__(self):
        self.items.dispatch_to_ui()
        self.selected_item.dispatch_to_ui()
        self.item_count = self.items.map(lambda items: len(items))
        self.has_items = self.item_count.map(lambda count: count > 0)

    def add_item(self, text: str):
        with batch():
            current = self.items.value
            self.items.value = current + [{"text": text, "done": False}]
```

In this structure, the View does not mutate low-level state directly.
It only invokes ViewModel methods, while rendering uses Observable-derived values.

```python
import nuiitivet as nv
from nuiitivet import material

class TodoView:
    def __init__(self, vm: TodoViewModel):
        self.vm = vm

    def build(self):
        return nv.Column(
            children=[
                material.Text(text=self.vm.item_count.map(lambda c: f"Items: {c}")),
                material.FilledButton(
                    text="Add",
                    on_click=lambda: self.vm.add_item("New item")
                ),
            ]
        )
```

## Derived State Composition

Use derived state composition when one value should be computed from other observables.
This keeps calculation logic in one place and avoids duplicating the same formula across multiple views.
It also makes changes safer because you only update the derivation once.

```python
from nuiitivet.observable import Observable, combine

class ShoppingCart:
    items = Observable([])
    tax_rate = Observable(0.1)

    def __init__(self):
        self.subtotal = self.items.map(
            lambda items: sum(item["price"] * item["qty"] for item in items)
        )
        self.total = combine(self.subtotal, self.tax_rate).compute(
            lambda sub, rate: sub * (1 + rate)
        )
```

## Memory Management with `Disposable`

Use `Disposable` for long-lived objects that own multiple subscriptions or derived observables.
By registering disposables in one place, you can release resources deterministically and prevent leaks.
This pattern is especially useful for screens or services with explicit lifecycle boundaries.

```python
from nuiitivet.observable import Disposable, Observable

class ViewModel(Disposable):
    def __init__(self):
        super().__init__()
        self.count = Observable(0)
        self.doubled = self.count.map(lambda x: x * 2)
        self.add_disposable(self.doubled)

    def dispose(self):
        super().dispose()
```

## Async Data Fetch Recipe

Use this pattern when data is loaded on a worker thread but rendered in the UI.
The key point is to keep UI-facing observables dispatched to the UI thread while tracking loading and error state explicitly.
This gives you predictable rendering for success, loading, and failure paths.

```python
import threading
from nuiitivet.observable import Observable

class DataViewModel:
    data = Observable([])
    loading = Observable(False)
    error = Observable(None)

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

- [State Management Overview](../observable.md)
- [Async & Threading Guide](../threading.md)
