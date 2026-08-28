# Translating foreign-framework habits into Nuiitivet

This is the core reference. Nuiitivet borrows *surface* ideas from Flutter,
SwiftUI, Jetpack Compose, React, and Rx — so the wrong version below is almost
always valid Python, which is exactly why it slips in. When you feel the reflex
to write the left column, write the right column instead.

## Table of contents

- [Imports & entry point](#imports--entry-point)
- [Component definition](#component-definition)
- [State & reactivity](#state--reactivity)
- [Layout, sizing & spacing](#layout-sizing--spacing)
- [Decoration & behavior (modifiers)](#decoration--behavior-modifiers)
- [Navigation & dialogs](#navigation--dialogs)

## Imports & entry point

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| `from nuiitivet.widgets import Column, Text` (scattered imports) | `import nuiitivet.material as nv`, then `nv.Column`, `nv.Text` — one import root |
| `runApp(MyApp())` (Flutter) | `nv.App(nv.Window(content=build_root)).run()` — pass a **factory** for hot reload |
| `MaterialApp(home=...)` (Flutter) | `nv.App(nv.Window(content=...))`; theming via `nv.App(win, theme=nv.ThemeFactory...)` |
| `nv.App(content=..., title=...)` (older nuiitivet) | `nv.App(nv.Window(content=..., title=...))` — `App` takes its main `Window`; window keywords (`title`, `width`, `menu`, ...) live on `Window`, and `App` keeps only `theme=` / `exit_policy=` |

```python
# Correct — a root factory keeps hot reload working (don't call it)
import nuiitivet.material as nv

def build_root() -> nv.Widget:
    return CounterApp()

def main() -> None:
    nv.App(nv.Window(content=build_root, title="Counter")).run()
```

## Component definition

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| `class X(StatelessWidget)` / `StatefulWidget` (Flutter) | `class X(nv.ComposableWidget)` |
| `createState()` / `initState()` / `dispose()` lifecycle overrides | Plain `__init__` to create `Observable`s; override `on_mount()` for setup that needs the tree (an `X.of(self)` lookup, async loading) |
| `onAppear` / `onDisappear` (SwiftUI) | `on_mount()` / `on_unmount()` — SwiftUI's `onAppear` fires on *tree insertion*, which is exactly `on_mount`, despite the name |
| `RouteAware` / `didPushNext` / `didPopNext` (Flutter) | No equivalent exists: a covered route stays mounted and nothing fires. Pause/resume from the side causing it — the code calling `push()`, or the `Observable` behind a `nv.Deck` index |
| `LaunchedEffect(Unit)` / `DisposableEffect` (Compose) | An `on_mount()` override runs once per instance; from inside `build()` use `nv.on_mount(cb)` plus a flag owned outside the rebuilt subtree |
| `def build(self, context):` (Flutter signature) | `def build(self):` |
| `@Composable def X()` (Compose) | a `ComposableWidget` subclass with `build(self)` |
| React function component returning JSX | `build(self)` returning a widget tree |

```python
# Correct
class CounterApp(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = nv.Observable(0)

    def build(self):
        return nv.Column([
            nv.Text(self.count.map(str)),
            nv.Button("Add", on_click=self.inc),
        ])

    def inc(self):
        self.count.value += 1
```

## State & reactivity

The deepest source of leaks. Nuiitivet state is `Observable`; the UI **binds** to
it. You never write code that pushes a value into a widget.

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| `self.setState(() => count++)` (Flutter) | `self.count.value += 1` |
| `const [count, setCount] = useState(0)` (React) | `self.count = nv.Observable(0)` |
| `useEffect(...)`, `useMemo(...)`, `useRef(...)` | derive with `combine().compute()` / `map()`; hold refs as plain attributes |
| `count.subscribe(lambda v: label.set_text(v))` (Rx habit) | pass the Observable in directly: `nv.Text(self.count)` |
| `derived = computed(() => a + b)` (MobX/Vue) | `self.total = self.a.combine(self.b).compute(lambda a, b: a + b)` |
| manual `.subscribe()` to trigger a re-render | not needed — binding regenerates the affected region automatically |
| `source.debounce(0.3).subscribe(cb)` as a bare statement (Rx habit: the source owns the subscription, so dropping the handle is normal) | hold what you derive — name it, or keep the `Disposable`: `self.bind(source.debounce(0.3).subscribe(cb))`. Held by nothing, it is collected and never fires |
| `source.where(lambda v: ...)` / `source.select(lambda v: ...)` (Rx/LINQ) | `source.filter(pred, initial=...)` and `source.map(fn)`. `initial` is required and keyword-only: a filtered Observable has no value of its own until something passes, and the caller decides what the UI shows meanwhile |
| hop back to the UI thread before writing state (`runOnUiThread`, `DispatchQueue.main`, a hand-rolled queue) | assign `self.x.value` from the worker directly — cross-thread writes are marshalled |
| `CancellationToken` / `CancellationTokenSource` (.NET), `AbortController` (JS), `Job.cancel()` (Kotlin), `takeUntil(cancel$)` (Rx) | for work derived from an Observable's value, `switch_map` supersedes the previous run for you and hands `fn` a `nv.CancelToken`. Otherwise there is no cancellation API: one `threading.Event` per run, passed to the worker, checked with `cancel.is_set()` |
| `switchMap` / `flatMapLatest` (Rx), `collectLatest` (Kotlin), a `useEffect` that aborts the previous fetch | `source.switch_map(fn, initial=...)` — same name, same semantics. `fn` takes `(value, cancel)`, runs off the UI thread, and must **return** failure as a value rather than raising; there is no `.error` channel |
| `.map(fetch)` / `.map(search_api)` — an async call inside a `map` (Rx habit, where `map` is on a stream) | `switch_map(fn, initial=...)`. A `map`/`compute` function is **synchronous** and runs on the triggering thread — the UI thread for a `debounce` chain — so I/O in it freezes the window, and two in-flight calls have no ordering guarantee |
| `TextEditingController()` + `controller:` (Flutter), a `ref` on an input (React) | bind an Observable as the field's value: `self.query = nv.Observable("")` then `nv.TextField(value=self.query)`. Edits are written back into it, and you set the text by assigning `self.query.value` — there is no controller object and no `.text` property to read |
| `onEditingComplete` (Flutter), a `FocusNode` listener, an `onBlur` handler (JS) to finish a value | `on_focus_change(focused, source)` on the field — the same signature as `nv.focusable()`. Branch on `focused`; it can arrive more than once as `True` when the input source changes, and once as `False` |
| `onSubmitted` expected to fire when the field loses focus | it does not. `on_submit` is **Enter only**, every press including a repeat on an unchanged value. Blur-time work goes to `on_focus_change` |
| `Observable<AsyncValue<T>>` / `Resource<T>` / `RemoteData` wrappers around loading + error (Flutter/Compose/Elm) | keep the value position plain and put failure in your own result type: `SearchOutcome(items=..., error=...)`. A wrapper type forces every downstream `map`/`filter`/`combine` and every binding to unwrap it |

Note: `Observable.subscribe()` **does** exist and is legitimate for side effects
(logging, calling a service). It is *only* an anti-pattern when used to manually
push a value into the UI — that is what binding is for.

```python
# Correct: derived + async, both bound straight into the UI
self.total   = self.a.combine(self.b).compute(lambda a, b: a + b)   # derived, synchronous
self.outcome = self.query.debounce(0.3).switch_map(self._search, initial=SearchOutcome())
# ... in build(): nv.Text(self.total), and bind self.outcome.map(lambda o: o.items) to a list
```

See [state.md](state.md) for the full API and the ViewModel pattern.

## Layout, sizing & spacing

Nuiitivet's signature difference: **size / alignment / spacing are parameters of
a widget, not widgets in their own right.** This kills Flutter's nesting hell.

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| `Padding(padding: EdgeInsets.all(12), child: X)` | `X(..., padding=12)` |
| `SizedBox(width: 200, child: X)` | `X(..., width=200)` |
| `Container(alignment: center, child: X)` | `X(..., alignment="center")` |
| `EdgeInsets.symmetric(...)` / `EdgeInsets.only(...)` | `padding=...` (number or per-side tuple) |
| `Column(children: [SizedBox(height: 20), ...])` for gaps | `nv.Column([...], gap=20)` |
| `cross_alignment="stretch"` / `align-items: stretch` (CSS) | alignment is positioning only: use `start`/`center`/`end`; to fill, size the child (`width="wt"`) |
| `main_alignment="flex-start"` / `"flex-end"` (CSS) | `"start"` / `"end"` |
| `alignment="baseline"` / `"fill"` (CSS) | not supported — position with `start`/`center`/`end`, size with `width`/`height` |
| `.map((e) => Widget(e)).toList()` for dynamic lists | `nv.Column.builder(items, lambda item, i: ...)` |
| `ListView.builder(itemBuilder: ...)` | `nv.Column.builder(...)` / `Row.builder` / `Flow.builder` |
| `LayoutBuilder(builder: (ctx, constraints) => ...)` (Flutter) | `X.modifier(nv.on_size_changed(self._on_size))` on the widget being measured |
| `MediaQuery.of(context).size` (Flutter) | `nv.Geometry.of(self).size` — the root provider tracks the window |
| `GeometryReader { geo in ... }` (SwiftUI) | `nv.on_size_changed` on the region; `nv.Geometry(Panel(), width="wt")` only if a *subtree* must read it |
| `BoxWithConstraints { maxWidth ... }` (Compose) | same — measure the filling widget with `nv.on_size_changed` |
| overriding `set_layout_rect` to publish a size | never needed: `nv.on_size_changed` reports it, `Geometry` publishes it to a subtree |

```python
# Correct
nv.Text("Hello", padding=12, width=200)              # not Padding(SizedBox(Text))
nv.Column([a, b, c], gap=20, padding=20)             # gap, not spacer widgets
nv.Column.builder(self.items, lambda item, i: nv.Text(item))   # reactive list from an Observable
```

See [layout.md](layout.md) for sizing policies, `builder()` vs `ForEach`, grids,
and adaptive layout with `on_size_changed`.

## Decoration & behavior (modifiers)

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| wrap `GestureDetector(onTap:, child: Button())` | `Button("OK").modifier(clickable(...))` |
| wrap `DecoratedBox(decoration:, child:)` | `X.modifier(background(...) \| corner_radius(...))` |
| `Tooltip(message:, child: X)` as a wrapper reflex | `X.modifier(tooltip("..."))` (tooltip is a modifier here) |
| `.modifier(a).modifier(b)` (re-wrapping) | compose in one call: `.modifier(a \| b \| c)` |
| Compose `Modifier.padding().background()` chain | `.modifier(...)` for decoration/behavior; padding is a widget **parameter** |

Modifier functions live on `nv`: `background`, `border`, `corner_radius`, `clip`,
`shadow`, `opacity`, `tooltip`, `clickable`, `focusable`, `hoverable`, `translate`,
`rotate`, `scale`, `visible`, … (there is **no** `radius` — it is `corner_radius`).

```python
# Correct
nv.Button("OK").modifier(
    tooltip("Submit") | clickable(on_click) | background("#2196F3")
)
```

## Navigation & dialogs

Reach `Navigator` / `Overlay` through an instance resolved from a mounted widget:
`nv.Navigator.of(self)` / `nv.Overlay.of(self)`. Each returns the nearest enclosing
one, falling back to the app's; add `root=True` to force the app's. They are **not**
static `nv.Navigator.push(...)` calls, and there is no `.root()` accessor (#518).

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| `Navigator.of(context).push(MaterialPageRoute(builder: ...))` | `nv.Navigator.of(self).push(CartScreen())`, or Intent-based routing |
| `Navigator.pop(context)` | `nv.Navigator.of(self).pop()` |
| `showDialog(context:, builder:)` returning a Future | `await nv.Overlay.of(self).dialog(nv.BasicDialog(...))` |
| close a dialog with a result | `overlay.close(value)` (not `Navigator.pop(value)`) |
| `ScaffoldMessenger.of(context).showSnackBar(...)` | `nv.Overlay.of(self).snackbar("Saved")` |
| `showSearch(context:, delegate: SearchDelegate())` (Flutter) — a full-screen search route | There is **no full-screen search widget**. Put `nv.SearchBar(...)` in a screen you lay out yourself, and push that screen like any other; or use `nv.DockedSearchBar(..., content=...)` for a dropdown. The bar animates its own 24dp → 12dp inset either way |
| routing tables of string paths only | Intent-based `nv.Navigator.intents(initial_route=..., routes={Intent: lambda i: Screen()})` |

```python
# Correct
overlay = nv.Overlay.of(self)
handle = overlay.dialog(
    nv.BasicDialog(title=nv.Text("Confirm"), content=nv.Text("Sure?"),
                   actions=[nv.Button("Yes", on_click=lambda: overlay.close(True))]))
result = await handle          # OverlayResult; read result.value
nv.Navigator.of(self).push(CartScreen())
```

See [navigation.md](navigation.md) for Intent-based routing, nested navigation,
and the ViewModel-friendly navigator/overlay injection patterns.
