---
layout: default
---

# Threading Model

nuiitivet is designed with a strict threading model to ensure stability and predictability.

## The Golden Rule

**All UI operations must happen on the main thread (UI thread).**

This includes:

- Creating widgets
- Modifying widget properties
- Layout and Paint operations
- Mounting and Unmounting widgets

Violating this rule will raise a `RuntimeError` in debug mode.

## Working with Background Threads

You can perform expensive operations (network requests, heavy computation) on background threads. However, you must be careful when updating the UI with the results.

### Using Observables

The recommended way to communicate from a background thread to the UI thread is using `Observable` with `dispatch_to_ui()`.

```python
import threading
import time
import nuiitivet as nv

class MyState:
    # Define an observable
    progress = nv.Observable(0.0)

    def __init__(self):
        # Enable UI dispatching for this observable
        self.progress.dispatch_to_ui()

    def start_work(self):
        threading.Thread(target=self._worker).start()

    def _worker(self):
        for i in range(101):
            time.sleep(0.1)
            # Safe to update from background thread
            # The framework will coalesce updates and dispatch to UI thread
            self.progress = i / 100.0

```

### Coalescing

When `dispatch_to_ui()` is enabled, rapid updates from a background thread are automatically coalesced. If the worker thread produces updates faster than the UI can process them, the UI will only receive the latest value when it's ready to process the next frame. This prevents the UI event loop from being flooded.

### Computed Observables

`ComputedObservable` also supports `dispatch_to_ui()`. If a computed observable depends on values that change on background threads, you can enable dispatching on the computed observable to ensure its subscribers (usually UI widgets) are notified on the UI thread.

```python
# If 'raw_data' updates on background thread
processed_data = raw_data.map(lambda d: process(d)).dispatch_to_ui()
```

## Testing

For testing code that involves threading and `dispatch_to_ui`, you can use the `mock_clock` fixture (if available in your test suite) or mock `pyglet.clock.schedule_once` to control when UI events are processed.
