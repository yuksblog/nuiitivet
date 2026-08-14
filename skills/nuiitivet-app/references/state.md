# State & reactivity (Observable)

`Observable` is Nuiitivet's state primitive. It binds directly to the UI (like
Signals) and carries Rx-style operators (like ReactiveProperty, its inspiration).
The rule that prevents 90% of leaks: **assign `.value`, bind the Observable into
the widget, never manually push into the UI.**

## Basic API

```python
import nuiitivet.material as nv

name  = nv.Observable("Alice")
count = nv.Observable(0)
items = nv.Observable([])

current = count.value        # get
count.value = current + 1    # set  -> bound UI updates automatically
```

A lambda cannot assign, so writes in expression position — callback props,
`subscribe` lambdas — use `set()` instead. Never `setattr(obs, "value", v)`:

```python
nv.Button("Increment", on_click=lambda: count.set(count.value + 1))
```

Same write path as `.value =` (same de-duping, `compare`, batching, dispatch);
prefer `.value =` wherever a statement fits.

Custom equality when needed (keyword-only `compare`):

```python
always = nv.Observable(0, compare=lambda a, b: False)
user   = nv.Observable(None, compare=lambda a, b: (a is b) if (a is None or b is None) else a.uid == b.uid)
```

## Binding into the UI

Pass the Observable itself where a value is expected — do not read `.value` at
build time if you want it to stay live, and do not `subscribe()` to update a
widget by hand. Widgets that take a string (e.g. `Text`) accept an
`Observable[str]`; map non-string state through `.map(...)` first:

```python
def build(self):
    return nv.Column([
        nv.Text(self.count.map(str)),                # rebinds when count changes
        nv.Button("Increment", on_click=self.inc),
    ])

def inc(self):
    self.count.value += 1                            # the Text follows on its own
```

## Derived state (declare a formula, not an update)

```python
self.a = nv.Observable(0)
self.b = nv.Observable(0)
# total recomputes whenever a or b changes; bind `self.total` straight into the UI
self.total = self.a.combine(self.b).compute(lambda a, b: a + b)
```

`map` is the single-source shorthand; `combine(...).compute(...)` derives from
several. A standalone `nv.Observable.compute(fn)` builds a computed value from any
Observables read inside `fn`.

## Async / event-stream state (Rx operators, then bind)

```python
self.query   = nv.Observable("")
self.results = self.query.debounce(0.3).map(search_api)   # thin the keystrokes, then map
# bind self.results into the UI like any other Observable
```

`throttle(seconds)` is the rate-limited sibling of `debounce`.

`filter(pred, initial=...)` updates only on values passing `pred`. **`initial` is
required and keyword-only** — a filtered Observable has no value of its own until
something passes, so the caller states what the UI shows meanwhile:

```python
self.valid_amount = self.amount.filter(lambda n: n > 0, initial=0)
```

Rejected values change nothing: no notification, and `.value` keeps reporting the
last one that passed. The source's current value is tested at construction too, so
`initial` shows only while nothing has passed. `pred` must be a pure function of
the value it is handed — reading another Observable inside it creates no
dependency and will not re-run the filter; use `combine` for that.

**Hold what you derive.** `q.debounce(0.3)` creates a new Observable, and like
every derived Observable it is collected unless something holds it — by name, or
by the `Disposable` that `subscribe()` returns:

```python
self.results = self.query.debounce(0.3).map(search_api)         # named -> held
self.bind(self.query.debounce(0.3).subscribe(self._on_query))   # bind keeps the Disposable
self._sub = self.query.debounce(0.3).subscribe(self._on_query)  # no bind()? keep it yourself

self.query.debounce(0.3).subscribe(self._on_query)              # nothing held -> never fires
debounced = self.query.debounce(0.3)                            # a local in __init__ is
debounced.subscribe(self._on_query)                             # ...gone when it returns
```

`debounce` / `throttle` / `filter` invite the mistake because they look like Rx streams,
where the source owns the subscription and dropping the handle is normal. The
local-variable spelling is the easy one to miss: it looks like setup, but nothing
survives the constructor.

**Bind one directly — `.value` is the last shaped emission.** A wrapper holds
what it last emitted, seeded from the source when it is built, so no `map()` is
needed to make it bindable:

```python
nv.Text(self.query.debounce(0.3))            # debounced
```

Until the first emission it reports the seed: `debounce` shows the value the
source had when the chain was built, `throttle` moves on the first change, and
`filter` shows `initial` until something passes.

Inline like that is safe even under "hold what you derive": the widget's binding
holds the wrapper, exactly as `subscribe()`'s `Disposable` does. What is *not*
safe is the local variable in `__init__` above — nothing binds it.

## Background work (threads)

Assign `.value` straight from a worker thread — the write is marshalled onto the
UI thread. No dispatch wrapper, no queue, no hop back.

```python
def start(self, path: str) -> None:
    threading.Thread(target=self._run, args=(path,), daemon=True).start()

def _run(self, path: str) -> None:
    self.rows.value = read_csv(path)      # marshalled; bound widgets just follow
```

- Marshalled writes land on the next tick and are **coalesced**: subscribers see
  the latest value per tick, not every value. Correct for anything rendered;
  wrong for a consumer that must see every value.
- Reading `.value` back on the worker right after writing returns the old value.
- `nv.Observable(0, dispatch=False)` opts out — synchronous, every value
  delivered — for state no widget binds to. Derivations inherit it.
- One-shot work with a result: `await asyncio.to_thread(fn, ...)` in an `async`
  handler and assign the result; no thread of your own.

### Cancellation

There is no cancellation primitive — a Python thread cannot be killed from
outside. Create a `threading.Event` **per run** and pass it to the worker:

```python
def start(self, path: str) -> None:
    self._cancel.set()                          # supersede the previous run
    cancel = self._cancel = threading.Event()   # this run's own flag
    threading.Thread(target=self._run, args=(path, cancel), daemon=True).start()

def _run(self, path: str, cancel: threading.Event) -> None:
    for index, row in enumerate(rows, start=1):
        if cancel.is_set():
            return
        self.imported_rows.value = index
```

Reusing one long-lived `Event` and calling `clear()` is the trap: the superseded
worker sees the flag down and resumes, so two runs write the same observables.
Guard `except` / `finally` writes with `cancel.is_set()` too, or a stale run
reports over a live one.

Unmounting does not stop a worker (its writes are inert, not unsafe). If the work
exists only for that screen, cancel from an `on_unmount()` override — not an
`on_unmount` modifier in `build()`, which fires on every rebuild.

## `subscribe()` — legitimate vs anti-pattern

`Observable.subscribe(fn)` returns a `Disposable`. **Always keep it.** In a widget
that means `self.bind(...)`, which disposes it at unmount:

```python
self.bind(self.user.subscribe(self._log_change))
```

- OK: side effects — logging, calling a service, analytics.
- Anti-pattern: subscribing to copy a value into a widget. That is what binding
  is for; pass the Observable into the widget instead.

Dropping the `Disposable` fails in one of two opposite ways, so neither symptom
points at the cause on its own:

| Subscribed to | Symptom |
| --- | --- |
| a plain Observable | the source holds the callback, so it keeps firing after unmount — into a dead tree |
| anything derived (`map`, `combine`, `debounce`, `throttle`, `filter`) | nothing holds the derived Observable, so it is collected and never fires at all |

## Initialization that must run exactly once

`Observable`s go in `__init__`. Setup that needs the widget **in the tree** —
`X.of(self)`, async loading — goes in an `on_mount()` override, which runs once
per instance: a rebuild replaces the built subtree, not the host.

```python
class DashboardScreen(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.rows = nv.Observable([])

    def on_mount(self):
        super().on_mount()
        self._load()                      # once; the tree is reachable here
```

Inside `build()` it is different: `X.modifier(nv.on_mount(cb))` registers on a
widget that is rebuilt every time, so guard it with a flag owned by something that
outlives the rebuild (the ViewModel). A flag on that widget dies with it.

No `on_appear()` / `on_disappear()` exists — a covered route stays mounted and
nothing fires. Pause/resume from the caller side, or a `nv.Deck` index Observable.

## ViewModel pattern

For non-trivial apps, separate state/logic into a ViewModel and keep `build()`
purely declarative. The View holds Observables (or the VM does) and the VM
exposes methods for event handlers to call. ViewModels should not import or
create Widgets — for dialogs/navigation they issue **Intents** to an injected
navigator/overlay, annotated with `nv.NavigatorProtocol` / `nv.OverlayProtocol` so the
VM stays free of widget types. See [navigation.md](navigation.md).
