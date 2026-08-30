# Navigation, dialogs & overlays

Principle: **structure is declarative, flow is imperative.** Screens and dialog
*content* are declared as widgets; *when* to show them is driven imperatively
from event handlers (often with `await`).

`Navigator` and `Overlay` are reached through an **instance**, resolved from a
widget — there is no global accessor:

- `nv.Navigator.of(self)` — the nearest enclosing navigator, falling back to the
  app's when there is no nested one.
- `nv.Overlay.of(self)` — the same rule for the overlay host of dialogs/snackbars.
- `nv.Navigator.of(self, root=True)` / `nv.Overlay.of(self, root=True)` — skip any
  nested one and target the app's.

There is **no** `Navigator.root()` / `Overlay.root()`; they were removed in #518
because a process-global root cannot say *which* app it belongs to. `self` must be
mounted, so resolve in `on_mount()`, `build()`, or the event handler — never in
`__init__`.

## Dialogs — declarative definition + imperative display

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
when driving it from a ViewModel — see the Intent section below.

## Snackbars — imperative fire & forget

```python
nv.Overlay.of(self).snackbar("Saved successfully!")          # optional: duration=5.0
```

A snackbar lives *inside* the window. To tell the user something finished while
they are in **another window**, raise an OS notification instead — no external
library, safe from any thread:

```python
nv.Desktop.notify("Import done", "1,000 rows written")   # fire-and-forget, never raises
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
| List → detail with back history | imperative `nv.Navigator.of(self).push(DetailScreen())` |
| From a ViewModel (decoupled, testable) | **Intent-based** routing |
| Per-region history (nested) | `nv.Navigator.of(self).push(...)` inside a nested `Navigator` |

Method names: `Navigator.of(self).push(screen_or_intent)` to go forward,
`Navigator.of(self).pop()` to go back. There is **no** `MaterialPageRoute`,
`push_replacement`, or `pop_until` — push a screen widget or an Intent; to replace
the whole screen from inside a nested navigator, use
`Navigator.of(self, root=True).push(...)`.

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
    # The navigator is passed per call, not stored: it cannot be resolved in
    # __init__ (see "Resolving a navigator / overlay" below).
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
                initial_route=HomeIntent(),
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

## Typing the injected navigator / overlay / window / app

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

## Resolving a navigator / overlay

**Never in `__init__`.** `nv.Navigator.of(self)` / `nv.Overlay.of(self)` walk up from
`self`, and a widget has no parent until it is attached to the tree — the call raises
`RuntimeError` with a message saying so.

Resolve one in `on_mount()`, `build()`, or the event handler, **every time**. This is
also why a VM takes the navigator/overlay per call rather than in its constructor.
