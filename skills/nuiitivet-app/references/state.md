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

## ViewModel pattern

For non-trivial apps, separate state/logic into a ViewModel and keep `build()`
purely declarative. The View holds Observables (or the VM does) and the VM
exposes methods for event handlers to call. ViewModels should not import or
create Widgets — for dialogs/navigation they issue **Intents** to abstract
interfaces (`IOverlay`, `INavigator`). See [navigation.md](navigation.md).
