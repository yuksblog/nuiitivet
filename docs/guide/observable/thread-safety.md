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

Use `.dispatch_to_ui()` for observables that drive UI rendering. Once enabled,
notifications are marshalled onto the UI thread, so subscribers can safely touch
widgets even when the value was set from a background thread.

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

## Rapid Updates Are Coalesced

When `.dispatch_to_ui()` is enabled, rapid updates from a background thread are
automatically coalesced: if the worker produces values faster than the UI can
process them, subscribers only receive the latest value on the next frame. This
keeps a busy worker from flooding the UI event loop, but it also means
intermediate values are dropped rather than queued — subscribers may not observe
every value the worker sets (e.g. a progress counter can skip numbers).

## Testing

To test code that relies on `.dispatch_to_ui()`, you need to control when the
queued UI notifications are delivered. Use the `mock_clock` fixture (if your test
suite provides one) or mock `pyglet.clock.schedule_once` so you can drive the
dispatch deterministically instead of waiting on a real frame.

---

## Next Steps

- [Patterns and Recipes](patterns-and-recipes.md)
- [State Management Overview](../observable.md)
