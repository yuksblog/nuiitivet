# Background Work: A CSV Import

[Thread Safety](thread_safety.md) covers the contract — what happens to a value
written from a worker thread. This page is the other half: how a real
long-running job is wired to a real screen.

One scenario runs through the whole page. The user picks a CSV file of a few
hundred thousand rows; the app reads it, validates every row, and writes the
survivors into its store. That takes long enough that the window must stay
responsive, show what is happening, and let the user give up.

## The state

The screen owns its state directly, as observables on the widget:

| Observable | Drives |
| --- | --- |
| `running` | Whether the progress bar is on screen at all |
| `step` | The line of text naming what the job is doing |
| `total_rows` | `0` until the file has been counted — which indicator to show |
| `imported_rows` | The numerator behind the progress bar |
| `error` | The failure message, `None` while things are fine |

```python
import threading

import nuiitivet.material as nv


class CsvImportScreen(nv.ComposableWidget):
    """Imports one CSV file on a worker thread."""

    running = nv.Observable(False)
    step = nv.Observable("")
    total_rows = nv.Observable(0)
    imported_rows = nv.Observable(0)
    error = nv.Observable(None)

    def __init__(self) -> None:
        super().__init__()
        self.progress = nv.combine(self.imported_rows, self.total_rows).compute(
            lambda done, total: done / total if total else 0.0
        )
        self.counting = self.total_rows.map(lambda total: total == 0)
```

`progress` and `counting` are derived, so the worker never writes them — it
writes the counts, and the derivations follow. Both inherit the marshalling of
their sources, so they are as safe to bind as the sources are.

Nothing here needs a separate ViewModel object. Splitting state out into one is
a structural choice about testing and reuse, unrelated to threads — see
[Patterns and Recipes](patterns_and_recipes.md#viewmodel-pattern) if you want
it. Everything on this page works the same either way.

## Indeterminate until the total is known

Before the file has been read there is no total, so there is no percentage to
show — but the job is already running and the screen has to say so. That is an
*indeterminate* progress bar, and once the row count is known the same strip
becomes a determinate one:

```python
    def build(self) -> nv.Widget:
        return nv.Column(
            gap=16,
            children=[
                nv.Text(self.step),
                nv.Deck(
                    index=self.counting.map(lambda counting: 0 if counting else 1),
                    children=[
                        nv.IndeterminateLinearProgressIndicator(width=320),
                        nv.LinearProgressIndicator(value=self.progress, width=320),
                    ],
                ).modifier(nv.visible(self.running)),
            ],
        )
```

Three bindings, three jobs:

- `Deck` keeps both indicators mounted and shows one, so the swap costs no
  rebuild and the bar does not jump.
- `visible(self.running)` keeps the strip off screen until there is something
  to report. An idle screen showing a progress bar is a screen lying about its
  state. `visible` leaves the space reserved, so nothing below it moves when
  the import starts.
- Every widget binds straight to an observable the worker writes; none of them
  knows a thread is involved.

A progress bar is the right shape here because the import has a place on the
screen and a duration worth watching. A short wait that simply blocks the
screen is the other case — a loading indicator over the screen, awaited rather
than tracked, as in [Thread
Safety](thread_safety.md#short-work-await-it-instead-of-managing-a-thread).

## The worker

```python
    def start(self, path: str) -> None:
        self.running.value = True
        threading.Thread(target=self._run, args=(path,), daemon=True).start()

    def _run(self, path: str) -> None:
        try:
            self.step.value = "Reading"
            rows = read_csv(path)
            self.total_rows.value = len(rows)

            self.step.value = "Importing"
            for index, row in enumerate(rows, start=1):
                store.insert(validate(row))
                self.imported_rows.value = index

            self.step.value = "Done"
        finally:
            self.running.value = False
```

`start()` returns immediately and the UI thread goes back to painting. Not one
line of the worker touches a widget: it writes observables, and nuiitivet
marshals each write onto the UI thread.

This is the job that owns its thread outright, rather than awaiting one through
`asyncio.to_thread`. Two reasons, and both show up below: the import reports
progress *while it runs*, so its state has to travel from the worker rather
than arrive as a return value; and it has to be interruptible, which an awaited
thread is not.

### Skipped values are the point

`imported_rows` is written once per row — potentially thousands of times per
frame. Those writes are [coalesced](thread_safety.md#what-marshalling-changes):
subscribers see the latest value per tick, not every value. A progress bar
wants exactly that. Rendering all 400,000 intermediate values would be both
impossible and pointless; the newest one is the only one that means anything.

The same applies to `step`. If two stages complete inside one frame, the
intermediate name never appears on screen. For a status line that is correct
behaviour — it is a display of *now*, not a log.

It stops being correct the moment something has to *count* the values rather
than render the newest. A per-row audit trail cannot be built from an
observable a widget binds to; give it its own `dispatch=False` observable, as
[Thread Safety](thread_safety.md#opting-out-dispatchfalse) describes.

## Cancelling

Marshalling carries values *to* the UI thread. Cancellation goes the other way
— the UI thread has to tell the worker to stop — and for that direction plain
`threading` is the whole answer:

```python
    def __init__(self) -> None:
        ...
        self._cancel = threading.Event()

    def start(self, path: str) -> None:
        self._cancel.clear()
        self.running.value = True
        threading.Thread(target=self._run, args=(path,), daemon=True).start()

    def cancel(self) -> None:
        self._cancel.set()      # called from on_click, on the UI thread
```

The worker checks the flag where it is cheap to stop — once per row:

```python
            for index, row in enumerate(rows, start=1):
                if self._cancel.is_set():
                    self.step.value = "Cancelled"
                    return
                store.insert(validate(row))
                self.imported_rows.value = index
```

`Event.set()` is safe from any thread and needs no marshalling: it is not a
value a widget renders. Wire it to a button and the screen never blocks —
`cancel()` returns instantly, and the worker notices on its next row.

```python
                nv.Button("Cancel", on_click=self.cancel, style=nv.ButtonStyle.tonal()),
```

## When the worker raises

An exception inside a worker thread kills that thread and nothing else. The
window keeps painting, the progress bar freezes at whatever it last showed, and
the user is told nothing. So catch it and route it into state, exactly like any
other outcome:

```python
    def _run(self, path: str) -> None:
        self.error.value = None
        try:
            ...
        except Exception as exc:
            self.error.value = str(exc)
            self.step.value = "Failed"
        finally:
            self.running.value = False
```

`error` is an ordinary observable, so the write from the `except` block is
marshalled like the rest and a widget can bind to it directly:

```python
                nv.Text(self.error.map(lambda message: message or "")),
```

Two rules worth keeping:

- **Clear the error where the job starts, not where it ends.** A stale message
  from the previous run is worse than none.
- **Reset the progress state in `finally`.** A failed run must not leave an
  indicator on screen forever.

## Putting it together

```python
class CsvImportScreen(nv.ComposableWidget):
    """Imports one CSV file on a worker thread."""

    running = nv.Observable(False)
    step = nv.Observable("")
    total_rows = nv.Observable(0)
    imported_rows = nv.Observable(0)
    error = nv.Observable(None)

    def __init__(self) -> None:
        super().__init__()
        self.progress = nv.combine(self.imported_rows, self.total_rows).compute(
            lambda done, total: done / total if total else 0.0
        )
        self.counting = self.total_rows.map(lambda total: total == 0)
        self._cancel = threading.Event()

    def start(self, path: str) -> None:
        self._cancel.clear()
        self.error.value = None
        self.imported_rows.value = 0
        self.total_rows.value = 0
        self.running.value = True
        threading.Thread(target=self._run, args=(path,), daemon=True).start()

    def cancel(self) -> None:
        self._cancel.set()

    def _run(self, path: str) -> None:
        try:
            self.step.value = "Reading"
            rows = read_csv(path)
            self.total_rows.value = len(rows)

            self.step.value = "Importing"
            for index, row in enumerate(rows, start=1):
                if self._cancel.is_set():
                    self.step.value = "Cancelled"
                    return
                store.insert(validate(row))
                self.imported_rows.value = index

            self.step.value = "Done"
        except Exception as exc:
            self.error.value = str(exc)
            self.step.value = "Failed"
        finally:
            self.running.value = False

    def build(self) -> nv.Widget:
        return nv.Column(
            gap=16,
            children=[
                nv.Text(self.step),
                nv.Deck(
                    index=self.counting.map(lambda counting: 0 if counting else 1),
                    children=[
                        nv.IndeterminateLinearProgressIndicator(width=320),
                        nv.LinearProgressIndicator(value=self.progress, width=320),
                    ],
                ).modifier(nv.visible(self.running)),
                nv.Text(self.error.map(lambda message: message or "")),
                nv.Row(
                    gap=12,
                    children=[
                        nv.Button(
                            "Import",
                            on_click=lambda: self.start("contacts.csv"),
                            style=nv.ButtonStyle.filled(),
                        ),
                        nv.Button("Cancel", on_click=self.cancel, style=nv.ButtonStyle.tonal()),
                    ],
                ),
            ],
        )
```

Threads, an `Event`, and observables — the widget is otherwise an ordinary
widget, and nothing in `build()` betrays that any of it happened off the UI
thread.

## Testing it

The worker's writes land through the clock, so a test pumps them rather than
sleeping. See [the `settle()` example](thread_safety.md#testing).

---

## Next Steps

- [Thread Safety](thread_safety.md)
- [Patterns and Recipes](patterns_and_recipes.md)
- [Threading Model](../advanced/threading.md)
