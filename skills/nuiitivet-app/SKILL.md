---
name: nuiitivet-app
description: Build, edit, and review Nuiitivet (Python UI framework) code with the correct idioms. Its surface resembles Flutter/SwiftUI/Compose/Rx, so agents leak foreign patterns; this skill front-loads Nuiitivet's own idioms and ships a linter to catch leaks. Use whenever writing or reviewing Nuiitivet UI code. For running, hot-reloading, and debugging a Nuiitivet app, see the nuiitivet-debug skill.
---

# Building Nuiitivet Apps

Nuiitivet is a Python UI framework. Its surface *resembles* other frameworks but
its idioms are its own. The single biggest failure mode is writing valid Python
that follows Flutter / React / Rx / Compose habits instead of Nuiitivet's. This
skill front-loads the correct idioms and provides a linter to catch leaks.

## The 7 core rules

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

5. **Decoration and behavior attach via `.modifier(...)`, composed with `|`.**
   `nv.Button("OK").modifier(tooltip("Submit") | background("#2196F3"))`. Do not
   wrap a widget to decorate it. (See the **Modifier catalog** for the set.)

6. **`App` takes its main `Window`; the root is a factory, not an instance.**
   The entry point is `nv.App(nv.Window(content=...))` — every window keyword
   (`title`, `width`, `menu`, ...) lives on `nv.Window`; `nv.App` takes only the
   window plus `theme=`, `exit_policy=`, and `tray=`. There is no
   `App(content=...)` form.
   Pass a zero-arg callable or a `Widget` subclass as `content` **without
   calling it** — `Window(content=build_root)` or `Window(content=Counter)`,
   never `Window(content=build_root())` (which silently disables live
   development); pass arguments through a closure
   (`Window(content=lambda: Home(cfg))`). Put per-tree state and side effects in
   the factory / widget `__init__`, not `main()` (which runs **once**, never on
   reload). The *why* and *how to run* live in the **nuiitivet-debug** skill.

7. **The one-line mental model:** Logic → UI is declarative (`Observable`
   binding); UI → logic is imperative (event handlers).

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
    nv.App(nv.Window(content=build_root, title="Counter")).run()   # pass build_root, NOT build_root()

if __name__ == "__main__":
    main()
```

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
| Switch the visible child by index (tabs, bottom-nav content, wizard steps) | `Deck` | `nv.Deck(index=obs, children=[PageA(), PageB()])` |
| Scroll a region | `VerticalScrollable` / `HorizontalScrollable` | `nv.VerticalScrollable(nv.Column([...]))` |
| Override one child's cross-axis position | `CrossAligned` | `nv.CrossAligned(child, "center")` |
| Rule / separator | `HorizontalDivider` / `VerticalDivider` | `nv.HorizontalDivider()` |
| Dynamic list from data | `Column.builder` (also `Row`/`Stack`/`Flow`/`UniformFlow`) | `nv.Column.builder(items_obs, lambda item, i: nv.Text(item))` |
| React to this widget's own measured size (adaptive placement, responsive reflow) | `on_size_changed` (modifier) | `X.modifier(nv.on_size_changed(self._on_size))` — reports `nv.Size` when it changes |

Background, border, shadow, and clipping are **modifiers** (see the Modifier
catalog below), not a job for `Container` — its box is layout-only.

**Content & media**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Text (static or bound) | `Text` | `nv.Text("Hi")` / `nv.Text(obs)` |
| Icon glyph | `Icon` | `nv.Icon("home")` |
| Image | `Image` | `nv.Image(path_or_source)` |
| Progress / loading | `CircularProgressIndicator` / `LinearProgressIndicator` / `LoadingIndicator` | `nv.LinearProgressIndicator(value=obs)` |
| Status badge | `SmallBadge` / `LargeBadge` | `nv.SmallBadge()` |
| Bundled / custom font | `Fonts` | `nv.Fonts.register("assets/fonts/NotoSansJP.ttf", family_name="NotoSansJP")` once at startup, before any widget renders; then `font_family="NotoSansJP"` wherever a `font_family` is accepted (`nv.TextStyle`; icon fonts via `nv.IconStyle(custom_font_family=...)`). App-wide default family: `nv.Fonts.set_default_family("Hiragino Sans")` (`None` restores locale-based detection) |

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
| Text input | `TextField` | `nv.TextField(value=obs, label="Name")` — `obs` is the value, written back as the user types; `on_change` only for a side effect. `on_submit` fires on Enter only, never on blur; use `on_focus_change(focused, source)` for blur-time work |
| Restricted text input | `TextField` + `input_filter` | `nv.TextField(value=obs, input_filter=nv.digits_only() \| nv.max_length(4))` |
| Search input | `SearchBar` | `nv.SearchBar(obs, placeholder="Search", width=440)` — `width` names the **box**; the bar is inset 24dp inside it (12dp while focused) |
| Search + dropdown panel | `DockedSearchBar` | `nv.DockedSearchBar(obs, placeholder="Search", content=panel_widget, on_submit=search, width=440)` — one slot, `content`: a live widget bound to your observables (suggestions, results, spinner), not a rebuild callback. Opens on focus, on a tap on the bar, and on typing; closes on Enter (`close_on_enter=False` keeps it up), on Escape, and on blur — but never on a tap on the bar itself; pass `is_open` to drive it yourself. `on_submit` is Enter only — clicking away never searches |
| Boolean toggle | `Checkbox` / `Switch` | `nv.Switch(checked=obs)` |
| Single choice | `RadioButton` / `RadioGroup` | `nv.RadioGroup(child, value=obs)` |
| Numeric / range slider | `HorizontalSlider` / `HorizontalRangeSlider` (+ vertical/centered variants) | `nv.HorizontalSlider(value=obs)` |
| Chips | `AssistChip` / `FilterChip` / `InputChip` / `SuggestionChip` | `nv.FilterChip("Tag", selected=obs)` |
| Date selection | `DockedDatePicker` | `nv.DockedDatePicker(value=text_obs, label="Arrival")` — `value` is the field's **text**; derive the date with `text_obs.map(nv.parse_date)`. The widget flags nothing: pass `is_error` / `supporting_text` derived from the same text. `min_date` / `max_date` scope the calendar only |
| Non-default date pattern | `DateFormat` | `fmt = nv.DateFormat("dd.mm.yyyy")`, then `date_format=fmt` on the widget and `text_obs.map(fmt.parse)` in the app — one object so parse, render and hint text cannot disagree. Tokens: `yyyy` `yy` `mm` `dd`, lowercase; everything else is a literal (`"yyyy年mm月dd日"` works) |
| Typed value from a text field | any text input | `obs.map(conv)` reports invalid as `None`; `obs.filter(pred, initial=seed).map(conv)` holds the last valid one. Never bind a widget to the typed value and mirror the text back — the widget writes into the text |

**Containers, navigation & overlays**

| Need | Widget | Canonical construction |
| --- | --- | --- |
| Content surface | `Card` | `nv.Card(child, ...)` |
| Left-hand app navigation | `NavigationRail` | `nv.NavigationRail([nv.RailItem("home", "Home"), ...], index=sel_obs)` |
| Contextual menu | `Menu` / `MenuItem` / `SubMenuItem` | `nv.Menu([nv.MenuItem("Save", on_click=fn)])` |
| Toolbar | `HorizontalFloatingToolbar` / `VerticalFloatingToolbar` | `nv.HorizontalFloatingToolbar([...])` |
| Sheets | `BottomSheet` / `SideSheet` / `StandardSideSheet` | `nv.Overlay.of(self).bottom_sheet(...)` |
| Dialog | `BasicDialog` via `Overlay` | `await nv.Overlay.of(self).dialog(nv.BasicDialog(...))` |
| Transient message | `Snackbar` via `Overlay` | `nv.Overlay.of(self).snackbar("Saved")` |
| OS desktop notification (a job finished while the user is in another window) | `Desktop.notify` | `nv.Desktop.notify("Import done", "1,000 rows written")` — fire-and-forget: never blocks, never raises, safe from any thread (the natural last line of a worker job). Delivery is best-effort (the OS may suppress it), so keep the result visible in-app too — in-app feedback is `Snackbar`, not this |
| Native open / save / folder dialog | `FileDialog` | `path = await nv.FileDialog.open_file(file_types=["txt", "md"])` — every method is a coroutine; call from an `async` handler. Cancel returns `None` (`open_files` returns `[]`) — never raises for cancel. Also `open_files(...)`, `save_file(default_name=...)`, `open_directory()`; extensions without the dot. Calls are serialized (one dialog at a time). Raises `nv.FileDialogError` when the dialog cannot be shown (Linux without `zenity`/`kdialog`) |
| Tooltip | `Tooltip` / `RichTooltip` (or the `tooltip` modifier) | `x.modifier(tooltip("..."))` |
| Screen-to-screen navigation | `Navigator` | `nv.Navigator.of(self).push(DetailScreen())` |
| Application menu bar | `MenuBar` / `MenuEntry` | `nv.Window(..., menu=nv.MenuBar([nv.MenuEntry("File", submenu=[nv.MenuEntry("Open", shortcut="Accel+O", on_select=fn), nv.MenuEntry.separator(), nv.MenuEntry.quit()])]))` — a window-level model, never in `build()`; `label`/`enabled`/`checked` take Observables; `shortcut` also fires window-wide (never duplicate it with `key_shortcut`); replace via `window.menu = ...`; `nv.MenuBarArea()` relocates the bar |
| Secondary / modal window | `Window` | `nv.Window(content=lambda: Palette(state), title="Palette").open()` — a model until `open()`; `close()` destroys it (construct a new one to reopen; state that must survive lives in app-layer Observables). Hiding is different: `window.hide()` parks an open window (tree, state, and geometry survive; no frames; still counts for the exit policy) and `window.show()` summons it back focused — `window.is_visible` is the matching Observable. Modal child: `nv.Window(content=..., parent=nv.Window.of(self), modal=True).open()`; content closes its own window via `nv.Window.of(self).close()`. First click into an inactive window acts on all platforms (macOS included, by default); `accepts_first_mouse=False` makes that click activate-only (macOS-only effect). Exit timing: `nv.App(win, exit_policy=nv.ExitPolicy...)` |
| System tray icon / resident app | `TrayIcon` | `nv.App(win, tray=nv.TrayIcon(icon="tray.png", tooltip="Sync", menu=[nv.MenuEntry("Open", on_select=lambda: win.show()), nv.MenuEntry.separator(), nv.MenuEntry.quit()]))` — App-owned, lives exactly as long as the app runs; the menu reuses `MenuEntry` (Observable `label`/`enabled`/`checked` update live; window-scoped roles are ignored; **always include `quit()`**). `tray.installed` (`Observable[bool]`) says whether the icon actually shows — install can fail (Linux desktops) without raising. Resident (close-to-tray) recipe, three independent parts: `exit_policy=nv.ExitPolicy.EXPLICIT` + `nv.Window(..., close_action=tray.installed.map(lambda ok: "hide" if ok else "close"))` + the tray; `win.hide()` before `run()` starts in the tray. macOS Dock: `dock_visibility="always" \| "auto" \| "never"` (ignored elsewhere) |

When a widget's exact parameters aren't covered here, the topical references
below carry the day-to-day set.

## Modifier catalog — decorate & attach behavior

Attach with `.modifier(...)`, composed with `|` in a single call (rule 5). Sizing
and spacing stay widget *parameters*, not modifiers.

**Decoration**

| Need | Modifier | Example |
| --- | --- | --- |
| Background fill | `background` | `background("#2196F3")` |
| Rounded corners | `corner_radius` | `corner_radius(12)` |
| Clip children to the shape | `clip` | `clip()` |
| Border / outline | `border` | `border("#888", 1)` |
| Drop shadow | `shadows` | `shadows(Shadow("#0003", blur_radius=16))` |
| MD3 elevation shadow | `shadows` | `shadows(elevation_shadows(2))` |
| Opacity | `opacity` | `opacity(0.5)` |
| Show / hide conditionally | `visible` | `visible(is_open)` |

**Interaction**

| Need | Modifier | Example |
| --- | --- | --- |
| Tap / click on any widget | `clickable` | `clickable(on_click)` |
| Focus + key handling | `focusable` | `focusable(on_key=handler)` |
| Hover handling | `hoverable` | `hoverable(on_hover)` |
| Tooltip on hover | `tooltip` | `tooltip("Submit")` |
| Receive OS file drops | `drop_target` | `drop_target(on_drop)` — `on_drop(e: nv.FileDropEvent)`; `e.paths` is `tuple[Path, ...]`, delivered to the innermost accepting widget under the drop point |

**Pointer participation**
which widget catches a click when layers overlap (default is `auto`; each takes `bool` / `Observable[bool]`)

| Need | Modifier | Example |
| --- | --- | --- |
| Transparent overlay must not steal clicks; children still work | `defer_pointer` | `defer_pointer()` |
| Composite acts as one non-interactive slab (children absorbed) | `absorb_pointer` | `absorb_pointer(disabled)` |
| Scrim / blocker: catch everywhere, block what's behind | `block_pointer` | `block_pointer(is_modal)` |
| Whole subtree is click-through (passes to what's behind) | `passthrough_pointer` | `passthrough_pointer(hidden)` |

**Transform**

| Need | Modifier | Example |
| --- | --- | --- |
| Move by an offset | `translate` | `translate((4, 0))` |
| Rotate | `rotate` | `rotate(90)` |
| Scale | `scale` | `scale(1.2)` |

## Gotchas

- **Widget-tree mutation is UI-thread only.** Never build, mount, or reassign a
  widget from a background thread. `Observable.value` is the exception: a write
  from a worker is marshalled onto the UI thread, so assign it directly — never
  hand-roll a dispatch wrapper or a queue drained from a timer.
- **Drawing is on-demand** — frames repaint when state changes, not on a fixed
  loop. Bind to an `Observable`; never drive animation with a per-frame `while`
  loop or busy polling.

## Workflow

1. **Read the matching reference first** — if the task touches state, layout, or
   navigation, read the topical reference below before writing.
2. **Write the code** following the core rules and the reference idioms.
3. **Confirm exact signatures by introspection, not memory.** The catalog names
   *what* to reach for; for precise params or a docstring, ask the installed
   package instead of trusting transcribed text:
   ```
   python -c "import inspect, nuiitivet.material as nv; print(inspect.signature(nv.NavigationRail.__init__)); print(inspect.getdoc(nv.NavigationRail))"
   ```
4. **Run the linter as the final step** and resolve every finding. The bundled
   `scripts/check_idioms.py` sits next to this `SKILL.md`; invoke it by its path
   in *your* install:
   ```
   python .claude/skills/nuiitivet-app/scripts/check_idioms.py <files-or-dirs>
   ```
   It reports foreign-framework patterns (warnings only — it does not edit code)
   and points at the correct Nuiitivet idiom. Fix each one by hand.

To **run, hot-reload, and debug** the app, switch to the **nuiitivet-debug**
skill — it owns the edit → see → act → verify loop.

## References — read the one matching the task

These files are **self-contained** — everything needed to write correct
day-to-day nuiitivet code is here, offline.

- **Any confusion about "how would another framework do this?"** →
  [references/translation.md](references/translation.md) — the core
  "tempted to write X → in Nuiitivet write Y" table. Read this first when unsure.
- **State, reactivity, derived/async values** →
  [references/state.md](references/state.md) — Observable, `combine`/`compute`,
  `map`/`debounce`/`filter`/`scan`, `switch_map` for async work, background threads and
  cancellation, ViewModel pattern.
- **Layout, sizing, spacing, dynamic lists, modifiers** →
  [references/layout.md](references/layout.md).
- **Navigation, dialogs, snackbars, overlays** →
  [references/navigation.md](references/navigation.md) — Navigator, Intent-based
  routing, Overlay.
