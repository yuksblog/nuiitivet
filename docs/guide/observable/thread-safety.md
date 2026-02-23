---
layout: default
---

# Observable: Thread Safety

## Problem

Updating an Observable from a worker thread can trigger UI updates outside the UI thread.

```python
# worker thread
viewmodel.data.value = result
# UI subscriber may crash if callback touches UI directly
```

## Solution: `.dispatch_to_ui()`

Use `.dispatch_to_ui()` for observables that drive UI rendering.

```python
import threading
from nuiitivet.observable import Observable

class ViewModel:
    data = Observable([])

    def __init__(self):
        self.data.dispatch_to_ui()

    def load_async(self):
        def worker():
            result = fetch_data()
            self.data.value = result

        threading.Thread(target=worker).start()
```

## Default Behavior

Without `.dispatch_to_ui()`, notifications run in the current thread for lower overhead.
This is suitable for pure logic-layer computations.

## Chain Placement

`.dispatch_to_ui()` can appear before or after other operators.

```python
total = (
    price
    .combine(quantity)
    .compute(lambda p, q: p * q)
    .dispatch_to_ui()
)
```

## Important Constraints

Inside compute/mapping functions:

- ✅ use observable values
- ❌ avoid direct UI widget access

```python
# good
text = count.map(lambda c: f"Count: {c}")

# then update widgets in subscribe callbacks
text.subscribe(lambda value: set_label_text(value))
```

---

## Next Steps

- [Patterns and Recipes](patterns-and-recipes.md)
- [State Management Overview](../observable.md)
