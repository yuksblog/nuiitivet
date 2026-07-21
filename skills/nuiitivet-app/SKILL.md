---
name: nuiitivet-app
description: Build, edit, and review Nuiitivet (Python UI framework) code with the correct idioms. Its surface resembles Flutter/SwiftUI/Compose/Rx, so agents leak foreign patterns; this skill front-loads Nuiitivet's own idioms (ComposableWidget, Observable, Column/Row, modifiers, Navigator/Overlay) and ships a linter to catch leaks. Use whenever writing or reviewing Nuiitivet UI code. For running, hot-reloading, and debugging a Nuiitivet app, see the nuiitivet-debug skill.
---

# Building Nuiitivet Apps

Nuiitivet is a Python UI framework. Its surface *resembles* other frameworks but
its idioms are its own. The single biggest failure mode is writing valid Python
that follows Flutter / React / Rx / Compose habits instead of Nuiitivet's. This
skill front-loads the correct idioms and provides a linter to catch leaks.

## The 6 core rules

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
   `SizedBox`, or `EdgeInsets` — that Flutter nesting does not exist. (`Container`
   *does* exist as a plain layout box, but reach for it only when you need a
   distinct single-child box, not merely to add padding or a size.)

5. **Decoration and behavior attach via `.modifier(...)` chained with `|`.**
   `nv.Button("OK").modifier(tooltip("Submit") | background("#2196F3"))`. Do not
   wrap a widget to decorate it.

6. **The app root is a factory, not an instance.** Pass a zero-argument callable
   (or a `Widget` subclass) to `nv.App(content=...)` **without calling it** —
   `App(content=build_root)`, never `App(content=build_root())`. Passing an
   already-constructed widget is what silently disables live development. The
   *why* (hot reload keeps `Observable` state alive across edits) and *how to run*
   live in the **nuiitivet-debug** skill.

The one-line mental model: **Logic → UI is declarative (Observable binding); UI →
logic is imperative (event handlers).**

## A complete minimal app

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

def build_root() -> nv.Widget:                     # <- the factory (rule 6)
    return Counter()

def main() -> None:
    nv.App(content=build_root, title="Counter").run()   # pass build_root, NOT build_root()

if __name__ == "__main__":
    main()
```

`main()` runs **once**; per-tree state and side effects belong in the factory /
widget `__init__`, not in `main()`. A `Widget` subclass works as `content`
directly (`App(content=Counter)`); a factory needing arguments closes over them
(`App(content=lambda: Home(cfg))`).

## Widget catalog — reach for the right one

All widgets hang off `nv`. This is the working set; every symbol is importable as
`nv.<Name>`. When intent maps to a widget below, use it rather than inventing one.

**Layout & structure**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Vertical / horizontal stack | `Column` / `Row` | `nv.Column([a, b], gap=8, padding=12)` |
| Single-child layout box (sizing, padding, alignment) | `Container` | `nv.Container(child, width=200, padding=16)` |
| Overlapping layers | `Stack` | `nv.Stack([base, floating])` |
| Wrapping / flowing children | `Flow` / `UniformFlow` | `nv.UniformFlow.builder(items, fn, columns=3)` |
| Switch between children by index (tabs/wizard) | `Deck` | `nv.Deck(index=obs, children=[PageA(), PageB()])` |
| Scroll a region | `VerticalScrollable` / `HorizontalScrollable` | `nv.VerticalScrollable(nv.Column([...]))` |
| Override one child's cross-axis position | `CrossAligned` | `nv.CrossAligned(child, "center")` |
| Rule / separator | `HorizontalDivider` / `VerticalDivider` | `nv.HorizontalDivider()` |
| Dynamic list from data | `Column.builder` (also `Row`/`Stack`/`Flow`/`UniformFlow`) | `nv.Column.builder(items_obs, lambda item, i: nv.Text(item))` |

Background, border, shadow, and clipping are **modifiers** (`background`,
`border`, `shadow`, `corner_radius`, `clip`), not a job for `Container` — its box
is layout-only.

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
  entry/exit; theming is `nv.ThemeFactory`. When a widget's exact parameters
  aren't covered here, the topical references below carry the day-to-day set.

## Threading & drawing gotchas

- **Widget-tree mutation is main-thread only.** Never build, mount, or reassign
  `Observable.value` that drives the tree from a background thread. Do async work
  off-thread, then hop back to the UI thread to update state. Reads are fine
  anywhere; mutation is not.
- **Drawing is on-demand.** Frames are painted when state changes, not on a
  fixed loop — do not write per-frame `while` loops or drive animation by busy
  polling; bind to an `Observable` and let the framework repaint.
- **Factory, not instance** (rule 6) — a stray `content=build_root()` silently
  disables live development.

## Running, hot-reloading & debugging

Writing the code is this skill's job. *Running* the app under hot reload,
inspecting and driving it through the dev bridge / MCP server (`status`,
`describe_tree`, `screenshot`, `click`, `wait_for`, …), and the
edit → see → act → verify loop live in the **nuiitivet-debug** skill. Reach for
it once there is an app to run.

## Workflow

1. Before writing, if the task touches an area below, read the matching reference.
2. Write the code following the 6 rules and the reference idioms.
3. **Always run the linter as the final step** and resolve every finding. Run the
   bundled script (`scripts/check_idioms.py`, sitting next to this `SKILL.md`) —
   invoke it by its path in *your* install, e.g.:
   ```
   python .claude/skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
   ```
   It reports foreign-framework patterns (warnings only — it does not edit code)
   and points at the correct Nuiitivet idiom. Fix each one by hand.

## References — read the one matching the task

These files are **self-contained** — everything needed to write correct
day-to-day nuiitivet code is here, offline. Read the local reference; you do not
need to fetch anything to do the work. If a case genuinely isn't covered, that
gap is a signal to extend these references (via the maintainer workflow), not to
go looking elsewhere.

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
