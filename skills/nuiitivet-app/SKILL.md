---
name: nuiitivet-app
description: Build, edit, and review applications with the Nuiitivet Python UI framework. Nuiitivet blends ideas from Flutter (widgets), SwiftUI/Compose (modifiers), and WPF ReactiveProperty (Observable state), so agents frequently leak idioms from those other frameworks. Use this skill whenever writing or modifying Nuiitivet UI code (ComposableWidget, Observable, App, Column/Row, modifiers, Navigator/Overlay), or when reviewing Nuiitivet code for foreign-framework patterns. Triggers include: creating a Nuiitivet app or widget, wiring state, adding navigation/dialogs, or checking that existing code follows Nuiitivet idioms rather than Flutter/React/Rx habits.
---

# Building Nuiitivet Apps

Nuiitivet is a Python UI framework. Its surface *resembles* other frameworks but
its idioms are its own. The single biggest failure mode is writing valid Python
that follows Flutter / React / Rx / Compose habits instead of Nuiitivet's. This
skill front-loads the correct idioms and provides a linter to catch leaks.

## The 5 core rules

1. **One import root.** `import nuiitivet.material as nv` — every symbol (layout,
   state, widgets, styles, modifiers) is reached through `nv`. Do not import
   widgets from scattered submodules or invent `from nuiitivet.widgets import ...`.

2. **UI components subclass `nv.ComposableWidget` and define `build(self)`.**
   There is no `StatelessWidget` / `StatefulWidget`, no `createState`, no
   `initState`, no `build(self, context)` signature. Create `Observable`s in
   plain `__init__`.

3. **State is `Observable`, and the UI binds to it — never push.** Assign
   `obs.value = x` and bound widgets update automatically. There is **no**
   `setState`, `useState`, or manual re-render. Do not `subscribe()` just to
   shove a value into a widget — pass the Observable straight into the widget.

4. **Size, spacing, and alignment are widget *parameters*, not wrapper widgets.**
   Write `nv.Text("Hi", padding=12, width=200)`. Do **not** wrap in `Padding`,
   `SizedBox`, `Container`, or `EdgeInsets` — that Flutter nesting does not exist.

5. **Decoration and behavior attach via `.modifier(...)` chained with `|`.**
   `nv.Button("OK").modifier(tooltip("Submit") | background("#2196F3"))`. Do not
   wrap a widget to decorate it.

The one-line mental model: **Logic → UI is declarative (Observable binding); UI →
logic is imperative (event handlers).**

## Hot-reload authoring — write a root factory, not a root instance

Nuiitivet apps are developed under in-process hot reload: edit a widget, save,
and the running window updates while `Observable` state survives. This works only
if the root is a **factory** — a zero-argument callable returning the root widget
— passed to `App(content=...)` **without calling it**:

```python
import nuiitivet.material as nv

class Counter(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)              # per-tree state: created here

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=16,
            children=[
                nv.Text(self.count.map(lambda n: f"Count: {n}")),
                nv.Button("increment", on_click=self._inc),
            ],
        )

    def _inc(self) -> None:
        self.count.value += 1

def build_root() -> nv.Widget:                     # <- the factory
    return Counter()

def main() -> None:
    nv.App(content=build_root, title="Counter").run()   # pass build_root, NOT build_root()

if __name__ == "__main__":
    main()
```

Rules that keep hot reload working:

- **Pass a factory, not an instance.** `App(content=build_root())` (with the
  call) yields a widget instance the reloader cannot rebuild — hot reload goes
  inert. A `Widget` *subclass* works directly too: `App(content=Counter)`. A
  factory needing arguments closes over them: `App(content=lambda: Home(cfg))`.
- **Per-tree init goes in the factory / widget `__init__`, not `main()`.**
  `main()` runs **once** at startup and never again on reload; side effects and
  module-level state there are not restored.
- Launch for development with `python -m nuiitivet.dev path/to/app.py` (or
  `--module pkg.app`); production launch (`App.run()`) is unchanged.

See the [Hot Reload guide](https://yuksblog.github.io/nuiitivet/guide/ai_pair_programming/hot_reload/).

## Widget catalog — reach for the right one

All widgets hang off `nv`. This is the working set; every symbol is importable as
`nv.<Name>`. When intent maps to a widget below, use it rather than inventing one.

**Layout & structure**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Vertical / horizontal stack | `Column` / `Row` | `nv.Column([a, b], gap=8, padding=12)` |
| Single-child box (background, sizing, clipping) | `Container` | `nv.Container(child, width=200, padding=16)` |
| Overlapping layers | `Stack` | `nv.Stack([base, floating])` |
| Wrapping / flowing children | `Flow` / `UniformFlow` | `nv.UniformFlow.builder(items, fn, columns=3)` |
| Switch between children by index (tabs/wizard) | `Deck` | `nv.Deck(index=obs, children=[PageA(), PageB()])` |
| Scroll a region | `VerticalScrollable` / `HorizontalScrollable` | `nv.VerticalScrollable(nv.Column([...]))` |
| Override one child's cross-axis position | `CrossAligned` | `nv.CrossAligned(child, "center")` |
| Rule / separator | `HorizontalDivider` / `VerticalDivider` | `nv.HorizontalDivider()` |
| Dynamic list from data | `Column.builder` (also `Row`/`Stack`/`Flow`/`UniformFlow`) | `nv.Column.builder(items_obs, lambda item, i: nv.Text(item))` |

**Content & media**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Text (static or bound) | `Text` | `nv.Text("Hi")` / `nv.Text(obs)` |
| Icon glyph | `Icon` | `nv.Icon("home")` (icon names are strings) |
| Image | `Image` | `nv.Image(path_or_source)` |
| Progress / loading | `CircularProgressIndicator` / `LinearProgressIndicator` / `LoadingIndicator` | `nv.LinearProgressIndicator(value=obs)` |
| Status badge | `SmallBadge` / `LargeBadge` | `nv.SmallBadge()` |

**Actions**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Text/filled/tonal/outlined button | `Button` | `nv.Button("Save", icon="save", on_click=fn, style=nv.ButtonStyle.filled())` |
| Icon-only button | `IconButton` / `IconToggleButton` | `nv.IconButton(icon="edit", on_click=fn)` |
| Floating action button | `Fab` / `ExtendedFab` / `FabMenu` | `nv.Fab(icon="add", on_click=fn)` |
| Grouped / segmented buttons | `ToggleButton` / `ConnectedButtonGroup` / `SplitButton` | `nv.ConnectedButtonGroup([...])` |

**Input & selection**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Text input | `TextField` | `nv.TextField(value=obs, label="Name")` |
| Boolean toggle | `Checkbox` / `Switch` | `nv.Switch(checked=obs)` |
| Single choice | `RadioButton` / `RadioGroup` | `nv.RadioGroup(child, value=obs)` |
| Numeric / range slider | `HorizontalSlider` / `HorizontalRangeSlider` (+ vertical/centered variants) | `nv.HorizontalSlider(value=obs)` |
| Chips | `AssistChip` / `FilterChip` / `InputChip` / `SuggestionChip` | `nv.FilterChip("Tag", selected=obs)` |
| Date selection | `DatePicker` / `ModalDatePicker` / `DockedDatePicker` | `nv.ModalDatePicker(...)` |

**Containers, navigation & overlays**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Content surface | `Card` | `nv.Card(child, ...)` |
| Left-hand app navigation | `NavigationRail` | `nv.NavigationRail([nv.RailItem("home", "Home"), ...], index=sel_obs)` |
| Contextual menu | `Menu` / `MenuItem` / `SubMenuItem` | `nv.Menu([nv.MenuItem("Save", on_click=fn)])` |
| Toolbar | `DockedToolbar` / `HorizontalFloatingToolbar` / `VerticalFloatingToolbar` | `nv.DockedToolbar([...])` |
| Sheets | `BottomSheet` / `SideSheet` / `StandardSideSheet` | `nv.Overlay.root().bottom_sheet(...)` |
| Dialog | `BasicDialog` via `Overlay` | `await nv.Overlay.root().dialog(nv.BasicDialog(...))` |
| Transient message | `Snackbar` via `Overlay` | `nv.Overlay.root().snackbar("Saved")` |
| Tooltip | `Tooltip` / `RichTooltip` (or the `tooltip` modifier) | `x.modifier(tooltip("..."))` |
| Screen-to-screen navigation | `Navigator` | `nv.Navigator.root().push(DetailScreen())` |

Notes:

- **Icons are string names**, not an enum: `icon="home"`, `leading_icon="save"`.
  (A typed constant `nv.Symbols.home` also exists for the same glyph.)
- "Add a menu on the left" → `NavigationRail`. "Bottom tabs" don't have a
  dedicated bar widget — switch content with a `Deck` keyed on an `Observable`.
- There is **no** `IndexedStack` or `BottomNavigationBar`; use `Deck` +
  `NavigationRail`.
- Wrappers (`FadeIn`/`FadeOut`/`ScaleIn`/`ScaleOut`/`SlideIn…`) animate a child's
  entry/exit; theming is `nv.ThemeFactory`. Consult the docs site for the full
  parameter set of any widget above.

## Threading & drawing gotchas

- **Widget-tree mutation is main-thread only.** Never build, mount, or reassign
  `Observable.value` that drives the tree from a background thread. Do async work
  off-thread, then hop back to the UI thread to update state. Reads are fine
  anywhere; mutation is not. See the
  [Threading guide](https://yuksblog.github.io/nuiitivet/guide/advanced/threading/).
- **Drawing is on-demand.** Frames are painted when state changes, not on a
  fixed loop — do not write per-frame `while` loops or drive animation by busy
  polling; bind to an `Observable` and let the framework repaint.
- **Factory vs instance** (see hot reload above) — a stray `content=build_root()`
  silently disables reload.

## How this fits the collaborative loop

This skill is the **authoring leg** of pair-programming over hot reload — it makes
the assistant *write the right nuiitivet code*. The other legs are framework
features (not knowledge), set up separately:

- **Write** — hot reload rebuilds the running app on save (see above).
- **See / act** — the dev bridge and its MCP server let an assistant inspect and
  drive the running app (`status` / `describe_tree` / `describe_state` /
  `screenshot` / `click` / `type` / `key` / `wait_for`). Three ways to *check*
  the app, cheapest first: **is it up and healthy?** → `status` (liveness, title,
  last-reload outcome, error count, and a `blank` flag for a white screen — no
  tree, no image); **is the right thing on screen?** → `describe_tree` (the
  structure, and how you resolve action targets); **do the pixels look right?** →
  `screenshot` (a last resort for genuine visual/layout checks — image tokens are
  expensive). Reach for `status` after startup or an edit, not `screenshot`.
  After an action that starts async work
  (network, a timer, an animation), call `wait_for` — naming a `key` / `label` /
  `text` condition, or `present=False` to wait one *out* — before `describe_tree`,
  so you observe the settled state instead of racing a spinner. Register it once
  in your MCP host with `python -m nuiitivet.dev mcp`
  (needs `pip install 'nuiitivet[mcp]'`); it is development-only and forwards to
  the running dev process. See the dev-bridge / MCP server docs for setup.
  - **Waiting on the human, not async work?** `wait_for` blocks your turn
    synchronously for up to `timeout` (default 3s), so it fits app-driven
    settling, not a person deciding when to click. To wait for a *human* action,
    keep each `wait_for` short and poll in a loop (re-issuing it, checking
    `interaction_log` between tries) rather than parking one call on a long
    `timeout` — the condition must land inside a call's live window to be seen,
    and a single long block ties up the turn while it waits.
- **Make a widget targetable** — attach a stable `key` with the `keyed()`
  modifier (`widget.modifier(keyed("increment-btn"))`) so the bridge can drive it
  by `key`, and its state survives a reorder across hot reload. Add it on demand
  and remove it once that need is gone. When chained with wrapping modifiers,
  apply `keyed()` **last**. See the
  [Other Modifiers guide](https://yuksblog.github.io/nuiitivet/guide/modifiers/others/#keyed).

With those in place the loop is **edit (hot reload) → see → act → verify → edit**,
and this skill keeps the "edit" step producing the correct widgets.

## Workflow

1. Before writing, if the task touches an area below, read the matching reference.
2. Write the code following the 5 rules and the reference idioms.
3. **Always run the linter as the final step** and resolve every finding:
   ```
   python skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
   ```
   It reports foreign-framework patterns (warnings only — it does not edit code)
   and points at the correct Nuiitivet idiom. Fix each one by hand.

## References — read the one matching the task

These files are **self-contained** — everything needed to write correct
day-to-day nuiitivet code is here, offline. Read the local reference; you do not
need to fetch anything to do the work.

- **Any confusion about "how would another framework do this?"** →
  [references/anti-patterns.md](references/anti-patterns.md) — the core
  "tempted to write X → in Nuiitivet write Y" table. Read this first when unsure.
- **State, reactivity, derived/async values** →
  [references/state.md](references/state.md) — Observable, `combine`/`compute`,
  `map`/`debounce`, ViewModel pattern.
- **Layout, sizing, spacing, dynamic lists, modifiers** →
  [references/layout.md](references/layout.md).
- **Navigation, dialogs, snackbars, overlays** →
  [references/navigation.md](references/navigation.md) — Navigator, Intent-based
  routing, Overlay.

The `https://yuksblog.github.io/nuiitivet/` links scattered through these files
are **optional deep-dives** for genuine edge cases (exhaustive parameter tables,
rare options) — open one only when the local reference doesn't cover your case,
not as a routine step. Reaching for the docs site every time wastes time and
tokens; the references exist precisely so you don't have to.
