# Navigation, dialogs & overlays

Principle: **structure is declarative, flow is imperative.** Screens and dialog
*content* are declared as widgets; *when* to show them is driven imperatively
from event handlers (often with `await`).

`Navigator` and `Overlay` are reached through an **instance**, never as static
calls:

- `nv.Navigator.root()` — the app's root navigator (available anywhere).
- `nv.Navigator.of(self)` — the nearest enclosing (possibly nested) navigator.
- `nv.Overlay.root()` — the root overlay host for dialogs/snackbars.

## Dialogs — declarative definition + imperative display

`Overlay.root().dialog(...)` shows a modal and returns a handle you can `await`
for an `OverlayResult` (read `result.value`). Close it with
`Overlay.root().close(value)` — **not** `Navigator.pop`.

```python
handle = nv.Overlay.root().dialog(
    nv.BasicDialog(
        title=nv.Text("Confirm"),
        content=nv.Text("Are you sure?"),
        actions=[
            nv.Button("Yes", on_click=lambda: nv.Overlay.root().close(True),  style=nv.ButtonStyle.text()),
            nv.Button("No",  on_click=lambda: nv.Overlay.root().close(False), style=nv.ButtonStyle.text()),
        ],
    )
)
result = await handle          # OverlayResult(value=..., reason=...)
if result.value:
    do_something()
```

Do **not** reach for Flutter's `showDialog(context:, builder:)`. A dialog can also
be presented from an **Intent** (`nv.Overlay.root().dialog(MyDialogIntent(...))`)
when driving it from a ViewModel — see the Intent section below.

## Snackbars — imperative fire & forget

```python
nv.Overlay.root().snackbar("Saved successfully!")            # optional: duration=5.0
```

## Tooltips — fully declarative (a modifier)

```python
nv.IconButton(icon="edit").modifier(tooltip("Click to edit"))
```

Name an icon with a string (`icon="edit"`) or the typed constant
`nv.Symbols.edit` — both resolve to the same glyph.

## Navigation patterns (pick by requirement)

| Need | Approach |
| --- | --- |
| Wizard / step switch inside one screen, no back history | switch children with a `Deck`: `nv.Deck(index=step_obs, children=[Step1(), Step2()])` |
| Tabs / rail, independent screens, keep state | `NavigationRail` + a `Deck` keyed on the selected-index `Observable` |
| List → detail with back history | imperative `nv.Navigator.root().push(DetailScreen())` |
| From a ViewModel (decoupled, testable) | **Intent-based** routing |
| Per-region history (nested) | `nv.Navigator.of(self).push(...)` inside a nested `Navigator` |

Method names: `Navigator.root().push(screen_or_intent)` to go forward,
`Navigator.root().pop()` to go back, `Navigator.of(self).push(...)` for the
nearest nested navigator. There is **no** `MaterialPageRoute`, `push_replacement`,
or `pop_until` — push a screen widget or an Intent; to replace the whole screen,
`push` from the root navigator while inside a nested one.

## Intent-based navigation (recommended from ViewModels)

A ViewModel issues an Intent to a navigator; the View maps Intents to screens with
the `nv.Navigator.intents(...)` factory. This keeps the VM free of Widget
knowledge and gives type-safe routing. Route builders return a **Widget**.

```python
from dataclasses import dataclass

@dataclass
class HomeIntent: pass

@dataclass
class DetailsIntent:
    item_id: int

class ItemViewModel:
    def __init__(self, navigator):          # the root navigator (or an INavigator)
        self.navigator = navigator
    def open(self, item_id: int):
        self.navigator.push(DetailsIntent(item_id=item_id))

def main():
    # rule 6: pass a factory, not an already-built Navigator, so live development works
    app = nv.App(
        content=lambda: nv.Navigator.intents(
            initial_route=HomeIntent(),
            routes={
                HomeIntent:    lambda _: HomeScreen(),
                DetailsIntent: lambda intent: DetailsScreen(item_id=intent.item_id),
            },
        ),
        title="Navigation Intent",
    )
    app.run()
```

The same Intent approach applies to dialogs from a ViewModel via `IOverlay` and an
overlay intent resolver.
