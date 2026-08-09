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

`throttle(seconds)` is the rate-limited sibling of `debounce`. Remember the
[threading rule](../SKILL.md): async results must be applied to `.value` on the
UI thread.

## `subscribe()` — legitimate vs anti-pattern

`Observable.subscribe(fn)` exists and returns a `Disposable` you can dispose. In
UI code cleanup is usually handled by the framework lifecycle.

- OK: side effects — logging, calling a service, analytics.
- Anti-pattern: subscribing to copy a value into a widget. That is what binding
  is for; pass the Observable into the widget instead.

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
