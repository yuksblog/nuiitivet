# Anti-patterns: foreign framework habits → the Nuiitivet way

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
| `runApp(MyApp())` (Flutter) | `nv.App(content=build_root).run()` — pass a **factory** for hot reload |
| `MaterialApp(home=...)` (Flutter) | `nv.App(content=...)`; theming via `nv.ThemeFactory` |

```python
# Correct — a root factory keeps hot reload working (don't call it)
import nuiitivet.material as nv

def build_root() -> nv.Widget:
    return CounterApp()

def main() -> None:
    nv.App(content=build_root, title="Counter").run()
```

## Component definition

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| `class X(StatelessWidget)` / `StatefulWidget` (Flutter) | `class X(nv.ComposableWidget)` |
| `createState()` / `initState()` / `dispose()` lifecycle overrides | Plain `__init__`; create `Observable`s there |
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

Note: `Observable.subscribe()` **does** exist and is legitimate for side effects
(logging, calling a service). It is *only* an anti-pattern when used to manually
push a value into the UI — that is what binding is for.

```python
# Correct: derived + async, both bound straight into the UI
self.total   = self.a.combine(self.b).compute(lambda a, b: a + b)   # derived
self.results = self.query.debounce(0.3).map(search_api)             # async, Rx-style operator
# ... in build(): nv.Text(self.total), and bind self.results to a list
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
| `cross_alignment="stretch"` / `align-items: stretch` (CSS) | alignment is positioning only: use `start`/`center`/`end`; to fill, size the child (`width="100%"` / `nv.Sizing.flex()`) |
| `main_alignment="flex-start"` / `"flex-end"` (CSS) | `"start"` / `"end"` |
| `alignment="baseline"` / `"fill"` (CSS) | not supported — position with `start`/`center`/`end`, size with `width`/`height` |
| `.map((e) => Widget(e)).toList()` for dynamic lists | `nv.Column.builder(items, lambda item, i: ...)` |
| `ListView.builder(itemBuilder: ...)` | `nv.Column.builder(...)` / `Row.builder` / `Flow.builder` |

```python
# Correct
nv.Text("Hello", padding=12, width=200)              # not Padding(SizedBox(Text))
nv.Column([a, b, c], gap=20, padding=20)             # gap, not spacer widgets
nv.Column.builder(self.items, lambda item, i: nv.Text(item))   # reactive list from an Observable
```

See [layout.md](layout.md) for sizing policies, `builder()` vs `ForEach`, grids.

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

Reach `Navigator` / `Overlay` through an instance — `nv.Navigator.root()` (or
`nv.Navigator.of(self)` for the nearest nested one), and `nv.Overlay.root()`.
They are **not** static `nv.Navigator.push(...)` calls.

| Tempted to write (foreign) | In Nuiitivet write |
| --- | --- |
| `Navigator.of(context).push(MaterialPageRoute(builder: ...))` | `nv.Navigator.root().push(CartScreen())`, or Intent-based routing |
| `Navigator.pop(context)` | `nv.Navigator.root().pop()` |
| `showDialog(context:, builder:)` returning a Future | `await nv.Overlay.root().dialog(nv.BasicDialog(...))` |
| close a dialog with a result | `nv.Overlay.root().close(value)` (not `Navigator.pop(value)`) |
| `ScaffoldMessenger.of(context).showSnackBar(...)` | `nv.Overlay.root().snackbar("Saved")` |
| routing tables of string paths only | Intent-based `nv.Navigator.intents(initial_route=..., routes={Intent: lambda i: Screen()})` |

```python
# Correct
handle = nv.Overlay.root().dialog(
    nv.BasicDialog(title=nv.Text("Confirm"), content=nv.Text("Sure?"),
                   actions=[nv.Button("Yes", on_click=lambda: nv.Overlay.root().close(True))]))
result = await handle          # OverlayResult; read result.value
nv.Navigator.root().push(CartScreen())
```

See [navigation.md](navigation.md) for Intent-based routing, nested navigation,
and the ViewModel-friendly `IOverlay` / `INavigator` patterns.
