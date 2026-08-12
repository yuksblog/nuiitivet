# Observable: Thread Safety

## The default is safe

An `Observable` written from a thread other than the UI thread marshals the
notification onto the UI thread for you. Subscribers therefore always run where
it is safe to touch widgets, whichever thread set the value.

```python
import threading
import nuiitivet.material as nv

class ViewModel:
    data = nv.Observable([])

    def load_async(self):
        def worker():
            self.data.value = fetch_data()   # safe: marshalled to the UI thread

        threading.Thread(target=worker).start()
```

There is nothing to enable. A write already on the UI thread stays synchronous
and pays only an integer thread check, so this costs nothing on the hot path.

## What marshalling changes

Two things follow from the write being deferred to the next tick, and both
matter when the writer is a worker thread:

- **The write is asynchronous.** Reading the value back on the worker
  immediately after setting it returns the *old* value; the new one lands on
  the next tick.
- **Rapid writes are coalesced.** If the worker produces values faster than the
  UI consumes them, subscribers see only the latest per tick. This keeps a busy
  worker from flooding the event loop, but intermediate values are dropped
  rather than queued — a progress counter can skip numbers.

Neither applies to writes made on the UI thread, which are applied inline.

## Opting out: `dispatch=False`

For an observable no widget will ever bind to — a value that lives entirely in
the logic layer — pass `dispatch=False`:

```python
class Pipeline:
    # Every step is consumed by a background stage, never by a widget.
    processed = nv.Observable(0, dispatch=False)
```

Notification then stays synchronous on the writing thread, and **every**
intermediate value is delivered rather than only the latest per tick. Reach for
it when a consumer counts steps rather than rendering the newest one.

Binding a widget to a `dispatch=False` observable and then writing to it from a
worker thread is the bug the default exists to prevent, so opt out only for
values you are sure the UI never sees.

### The opt-out propagates

Derivations of a logic-layer observable stay logic-layer:

```python
internal = nv.Observable(0, dispatch=False)
doubled = internal.map(lambda v: v * 2)      # also dispatch=False
```

`combine(...).compute(...)` follows the sources, dispatching unless **every**
source opted out — one source that expects marshalling is enough to need it.
Pass `dispatch=` explicitly to override either way.

## Testing

Under the pytest plugin, a test body runs on the UI thread, so ordinary writes
apply inline and need nothing special. A write from a worker thread is queued
on the clock, and `settle()` pumps it:

```python
def test_worker_update_reaches_the_tree(nuiitivet_app):
    app = nuiitivet_app(screen, size=(800, 600))

    worker = threading.Thread(target=lambda: setattr(vm.data, "value", "after"))
    worker.start()
    worker.join()

    app.settle()          # applies the queued write
    assert app.get(key="readout").text == "after"
```

A worker that keeps running while you settle is fine: work it arms is pumped,
but does not count towards the convergence bound, so a live background thread
never turns into `LayoutNotConvergedError`.

### Outside the harness

Without the harness you control delivery through the clock. The indirection
point is `nv.set_clock()`, not pyglet: nuiitivet schedules every deferred
notification through the installed clock, and the backend installs pyglet's at
startup.

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
  The fallback clock delivers on its own servicing thread, so subscribers must
  not touch widgets, and assertions have to wait on real time.

Restore the previous clock afterwards, or later tests inherit yours.

---

## Next Steps

- [Patterns and Recipes](patterns_and_recipes.md)
- [State Management Overview](index.md)
