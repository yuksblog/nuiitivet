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
import nuiitivet.material as nv

class ViewModel:
    data = nv.Observable([])

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
queued UI notifications are delivered. The indirection point is `nv.set_clock()`,
not pyglet: nuiitivet schedules every deferred notification through the installed
clock, and the backend installs pyglet's clock there at startup. Install your own
clock and tick it yourself.

```python
import threading
from typing import List, Tuple

import nuiitivet.material as nv


class ManualClock:
    """Queue scheduled callbacks and run them on demand.

    Structurally an `nv.Clock` — the protocol a clock has to satisfy.
    """

    def __init__(self) -> None:
        self._pending: List[Tuple[float, nv.ClockCallback]] = []

    def schedule_once(self, fn: nv.ClockCallback, delay: float) -> None:
        self.unschedule(fn)
        self._pending.append((delay, fn))

    def schedule_interval(self, fn: nv.ClockCallback, interval: float) -> None:
        self._pending.append((interval, fn))

    def unschedule(self, fn: nv.ClockCallback) -> None:
        # Compare by equality, not `is`: `obj.method` is a fresh object on
        # every access, so identity never matches and timers leak.
        self._pending = [entry for entry in self._pending if entry[1] != fn]

    def tick(self, dt: float = 0.0) -> None:
        pending, self._pending = self._pending, []
        for _, fn in pending:
            fn(dt)


def test_worker_update_reaches_subscribers():
    previous = nv.get_clock()
    manual = ManualClock()
    nv.set_clock(manual)
    try:
        vm = ViewModel()
        received = []
        vm.data.subscribe(received.append)

        thread = threading.Thread(target=vm.load_async)
        thread.start()
        thread.join()

        assert received == []  # still queued
        manual.tick()
        assert received == [expected]
    finally:
        nv.set_clock(previous)
```

Read the current clock with `nv.get_clock()`, never `nv.clock`: the latter is
bound when nuiitivet is imported, so it does not follow `nv.set_clock()` and
still points at the startup fallback long after the backend installed its own.

Two rules for a hand-rolled clock:

- **Match callbacks by equality (`==`), never by `is` or `id()`.** This is what
  `pyglet.clock` does, and nuiitivet relies on it — `unschedule(self._emit)`
  has to cancel a timer armed with `self._emit`, even though each attribute
  access produces a distinct bound-method object.
- **Prefer running callbacks synchronously on the thread that ticks the clock.**
  A `threading.Timer`-based clock delivers on a background thread, so
  subscribers must not touch widgets, and assertions have to wait on real time.

Restore the previous clock afterwards, or later tests inherit yours.

---

## Next Steps

- [Patterns and Recipes](patterns_and_recipes.md)
- [State Management Overview](index.md)
