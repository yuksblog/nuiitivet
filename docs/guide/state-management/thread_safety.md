# Observable: Thread Safety

## The default is safe

An `Observable` written from a thread other than the UI thread marshals the
notification onto the UI thread for you. Subscribers therefore always run where
it is safe to touch widgets, whichever thread set the value.

```python
import threading

import nuiitivet.material as nv


class CsvPreview(nv.ComposableWidget):
    rows = nv.Observable([])

    def load(self, path: str) -> None:
        def worker() -> None:
            self.rows.value = read_csv(path)   # safe: marshalled to the UI thread

        threading.Thread(target=worker, daemon=True).start()

    def build(self) -> nv.Widget:
        return RowTable(self.rows)
```

The table repaints with the file's contents and never learns that a worker
produced them. There is nothing to enable. A write already on the UI thread
stays synchronous and pays only an integer thread check, so this costs nothing
on the hot path.

## Short work: await it instead of managing a thread

The example above spawns its own thread because it has to be about a
cross-thread write. Most short jobs do not: they run once, the screen waits for
them, and the result is used the moment it arrives. For those, hand the thread
to the runtime and `await` it. Event handlers may be `async`, so this is a
handler like any other:

```python
import asyncio


class CsvPreview(nv.ComposableWidget):
    rows = nv.Observable([])

    async def _open(self) -> None:
        async with nv.Overlay.of(self).while_loading():
            rows = await asyncio.to_thread(read_csv, "contacts.csv")
        self.rows.value = rows

    def build(self) -> nv.Widget:
        return nv.Column(
            gap=16,
            children=[
                nv.Button("Open CSV…", on_click=self._open, style=nv.ButtonStyle.filled()),
                RowTable(self.rows),
            ],
        )
```

Two things fall out of this shape, and both are why it is worth preferring:

- **The wait shows itself.** MD3 renders a short, indeterminate wait as a
  loading indicator centred over the screen, and `while_loading()` owns that
  overlay for the duration of the block — opened on entry, closed on exit,
  including when the block raises. There is no handle to hold and no
  subscription to dispose, so no `on_mount` / `on_unmount` pair either.
- **The line after the `await` is back on the UI thread.** Only `read_csv` ran
  on a worker; the assignment does not, so it applies inline. Marshalling has
  nothing to do here — which is the point. It exists for values a worker
  publishes *while it is still running*, not for the result you awaited.

That second case — a job long enough to report progress and a current step
while it works, and to need a cancel button — is
[Background Work](background_work.md).

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

Coalescing is what you want for anything a widget renders: an import that
writes its row counter 400,000 times still paints one progress bar per frame,
showing the newest count. It is the wrong behaviour only when a consumer has to
see every value rather than the newest one.

## Opting out: `dispatch=False`

For an observable no widget will ever bind to — a value that lives entirely in
the logic layer — pass `dispatch=False`:

```python
class CsvImport:
    # Consumed by the audit-log writer on the worker thread, never by a widget.
    rejected_row = nv.Observable(0, dispatch=False)
```

Notification then stays synchronous on the writing thread, and **every**
intermediate value is delivered rather than only the latest per tick. Reach for
it when a consumer counts values rather than rendering the newest one — a log
that must record every rejected row cannot be built from an observable whose
intermediate values are dropped.

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

    worker = threading.Thread(target=lambda: setattr(vm.rows, "value", "after"))
    worker.start()
    worker.join()

    app.settle()          # applies the queued write
    assert app.get(key="readout").text == "after"
```

A worker that keeps running while you settle is fine: work it arms is pumped,
but does not count towards the convergence bound, so a live background thread
never turns into `LayoutNotConvergedError`.

Without the harness there is no `settle()`, and delivery is whatever the
installed clock does. [Testing outside the harness](../testing/clock.md) covers
driving a clock yourself.

---

## Next Steps

- [Background Work](background_work.md)
- [Patterns and Recipes](patterns_and_recipes.md)
- [State Management Overview](index.md)
