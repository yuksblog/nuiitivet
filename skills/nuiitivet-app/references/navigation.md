# Navigation, dialogs & overlays

Principle: **structure is declarative, flow is imperative.** Screens and dialog
*content* are declared as widgets; *when* to show them is driven imperatively
from event handlers (often with `await`).

## Resolve a navigator or an overlay

`Navigator` and `Overlay` are reached through an **instance**, resolved from a
mounted widget — there is no global accessor, and no `.root()`:

- `nv.Navigator.of(self)` — the nearest enclosing navigator, falling back to the
  app's when there is no nested one.
- `nv.Overlay.of(self)` — the same rule for the overlay host of dialogs/snackbars.
- `nv.Navigator.of(self, root=True)` / `nv.Overlay.of(self, root=True)` — skip any
  nested one and target the app's.

**Never in `__init__`.** The lookup walks up from `self`, and a widget has no
parent until it is attached to the tree — the call raises `RuntimeError` with a
message saying so. Resolve in `on_mount()`, `build()`, or the event handler,
**every time**. This is also why a ViewModel takes the navigator / overlay per
call rather than in its constructor.

## Navigate

| Need | Approach |
| --- | --- |
| Wizard / step switch inside one screen, no back history | switch children with a `Deck`: `nv.Deck(index=step_obs, children=[Step1(), Step2()])` |
| Tabs / rail, independent screens, keep state | `NavigationRail` + a `Deck` keyed on the selected-index `Observable` |
| List → detail with back history | imperative `nv.Navigator.of(self).push(DetailScreen())` |
| From a ViewModel (decoupled, testable) | **Intent-based** routing |
| Per-region history (nested) | `nv.Navigator.of(self).push(...)` inside a nested `Navigator` |

Method names: `Navigator.of(self).push(screen_or_intent)` to go forward,
`Navigator.of(self).pop()` to go back. There is **no** `MaterialPageRoute`,
`push_replacement`, or `pop_until` — push a screen widget or an Intent; to replace
the whole screen from inside a nested navigator, use
`Navigator.of(self, root=True).push(...)`.

## Show an overlay

### Dialogs

`Overlay.of(self).dialog(...)` shows a modal and returns a handle you can `await`
for an `OverlayResult` (read `result.value`). Close it with
`overlay.close(value)` — **not** `Navigator.pop`.

```python
overlay = nv.Overlay.of(self)
handle = overlay.dialog(
    nv.BasicDialog(
        title=nv.Text("Confirm"),
        content=nv.Text("Are you sure?"),
        actions=[
            nv.Button("Yes", on_click=lambda: overlay.close(True),  style=nv.ButtonStyle.text()),
            nv.Button("No",  on_click=lambda: overlay.close(False), style=nv.ButtonStyle.text()),
        ],
    )
)
result = await handle          # OverlayResult(value=..., reason=...)
if result.value:
    do_something()
```

Resolving the overlay once into a local also gives the action lambdas something to
close without repeating the lookup.

Do **not** reach for Flutter's `showDialog(context:, builder:)`. A dialog can also
be presented from an **Intent** (`nv.Overlay.of(self).dialog(MyDialogIntent(...))`)
when driving it from a ViewModel — see **Pass them to a ViewModel**.

### Snackbars

```python
nv.Overlay.of(self).snackbar("Saved successfully!")          # optional: duration=5.0
```

A snackbar lives *inside* the window. For something that finished while the user
is in another window, it is `nv.Desktop.notify` — see [desktop.md](desktop.md).

## Pass them to a ViewModel

### Route by Intent

A ViewModel issues an Intent to a navigator; the View maps Intents to screens with
the `nv.Navigator.intents(...)` factory. This keeps the VM free of Widget
knowledge and gives type-safe routing. A factory returns a **Widget**, or a
`(widget, transition)` pair.

```python
from dataclasses import dataclass

@dataclass
class HomeIntent: pass

@dataclass
class DetailsIntent:
    item_id: int

class ItemViewModel:
    # The navigator is passed per call, not stored: it cannot be resolved in
    # __init__ (see "Resolve a navigator or an overlay").
    def open(self, navigator: nv.NavigatorProtocol, item_id: int):
        navigator.push(DetailsIntent(item_id=item_id))

class HomeScreen(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = ItemViewModel()
    def build(self):
        return nv.Button(
            "Open",
            on_click=lambda: self.vm.open(nv.Navigator.of(self), item_id=42),
            style=nv.ButtonStyle.filled(),
        )

def main():
    # rule 6: pass a factory, not an already-built Navigator, so live development works
    app = nv.App(
        nv.Window(
            content=lambda: nv.Navigator.intents(
                initial=HomeIntent(),
                routes={
                    HomeIntent:    lambda _: HomeScreen(),
                    DetailsIntent: lambda intent: DetailsScreen(item_id=intent.item_id),
                },
            ),
            title="Navigation Intent",
        ),
    )
    app.run()
```

The same Intent approach applies to dialogs from a ViewModel via `nv.Overlay` and
an intent resolver.

### Type what the ViewModel receives

Annotate what a ViewModel receives with the protocols, not the concrete objects:

- `nv.NavigatorProtocol` — `push()`, `pop()`, `can_pop()`.
- `nv.OverlayProtocol` — `dialog()`, `snackbar()`, `loading()`, `while_loading()`,
  `side_sheet()`, `bottom_sheet()`, `close()`.
- `nv.WindowProtocol` — `close()`, `hide()`, `show()`, `minimize()`, `maximize()`,
  `restore()`, `full_screen()`, `center()`, `move_to()`, `resize()`, plus
  `is_open` / `is_visible` (Observables) and the awaitable `closed`.
- `nv.AppProtocol` — `exit()`, `set_theme()`, `register_themes()`. This is also
  the declared return type of `nv.App.of(context)`.

The concrete objects satisfy them structurally, so call sites are unchanged;
the VM becomes type-checkable and unit-testable against a hand-written fake with no
widget tree and no `App`. There is no `INavigator` / `IOverlay` — those names do not
exist.

`nuiitivet.OverlayProtocol` (core) is a *different, smaller* protocol carrying only
`close()`, mirroring how `nv.Overlay` is `MaterialOverlay` while core `Overlay` has no
`dialog` / `snackbar` / sheet helpers. From an app, use the `nv.` one.
