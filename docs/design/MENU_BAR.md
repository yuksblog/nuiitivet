# Menu Bar Design

Status: implemented (both stages: the in-app bar and the macOS NSMenu bridge).

## 1. Purpose and Scope

This document defines the design of the application menu bar: the declarative
menu model registered on `App`, its rendering on Windows/Linux as an in-app
widget, and its bridging to the global menu bar (`NSMenu`) on macOS.

### In scope

- The menu model (`MenuBar`, `MenuBarItem`) and its reactivity contract
- Registration on `App` and activation dispatch
- Placement rules, including free placement inside a `CustomChrome`
- Platform split: in-app rendering vs. the macOS `NSMenu` bridge
- Integration with the keyboard-shortcut system
  (`docs/design/KEYBOARD_SHORTCUTS.md`)
- Styling: the theme-extension palette and per-instance style (Section 8)

### Out of scope

- Context menus and dropdown menus attached to widgets — those are the
  existing MD3 `Menu` / `MenuItem` widgets (`src/nuiitivet/material/menu.py`)
- Tray icons and other desktop integration
- A general user-extensible command/intent system (see Section 9.2)

## 2. Terminology

- **menu model**: The plain declarative data tree (`MenuBar` and its items)
  registered on `App`. Not widgets.
- **in-app bar**: The Nuiitivet-drawn horizontal bar rendering the menu model
  on Windows/Linux.
- **global menu bar**: The macOS system menu bar at the top of the screen,
  driven through `NSMenu`.
- **standard item**: A prebuilt `MenuBarItem` factory (e.g. `quit()`) whose
  behavior and per-platform placement the framework owns.
- **accelerator**: The keyboard shortcut displayed next to an item and able to
  activate it while the menu is closed.

## 3. Design Decisions

1. **The menu is a model registered on `App`, not a widget in the tree.**
   On macOS the menu lives outside the window, so a widget-tree API would be
   a lie on one of the two platforms. `App(menu=...)` sits naturally beside
   `title=` and `chrome=`.
2. **One activation path: `on_select` callbacks.** There is no `intent=`
   parameter. `App.dispatch` is a closed set of built-in intents with no
   user-facing handler registry, so an `intent=` parameter could only ever
   invoke built-in commands — and standard items (Section 4.4) cover that
   better. No existing widget takes `intent=`; menu items follow suit.
3. **Item properties are `Observable`-bindable**, following the `title=`
   precedent on `App`. Structural changes are wholesale replacement, not
   diffing (Section 4.3).
4. **Accelerators are declared on the item and registered by the menu
   system.** One definition drives display, activation, and per-platform
   presentation (`⌘S` vs `Ctrl+S`). Declaring the same shortcut both on a
   menu item and via `key_shortcut()` is a conflict the app author must not
   create.
5. **Platform split**: Windows/Linux render an in-app bar whose popups reuse
   the MD3 `Menu` machinery; macOS bridges the same model to `NSMenu` via
   pyglet's bundled `cocoapy` (ctypes Objective-C bridge) — no new
   dependency.
6. **Styling follows the scrollbar precedent**: the menu bar is a generic
   (non-Material) widget, so an app-wide `MenuBarThemeData` is registered
   through the `ThemeExtension` seam by each design system, with a
   per-instance `MenuBarStyle` for geometry and overrides — and the palette
   drives the popups too, not only the bar (Section 8).

## 4. The Menu Model

### 4.1 Types

The model consists of two public types, defined in the framework-common
`nuiitivet/menubar/` package (Section 8.1) and re-exported through the
public surface:

- `MenuBar(items: Sequence[MenuBarItem])` — the root.
- `MenuBarItem` — a single entry. One type covers all roles, Electron-style:
  - **Action**: `MenuBarItem(label, on_select=..., shortcut=..., enabled=...,
    checked=...)`
  - **Submenu**: `MenuBarItem(label, submenu=[...])` — top-level bar entries
    ("File", "Edit") are simply items with a `submenu`. Nesting is unlimited.
  - **Separator**: `MenuBarItem.separator()`.

Construction-time validation: a non-separator item must have exactly one of
`on_select` or `submenu`, and `submenu` is mutually exclusive with
`shortcut` / `checked`. Violations raise immediately, not at render time.

The names avoid colliding with the existing MD3 widgets `Menu` / `MenuItem`
(`src/nuiitivet/material/menu.py`), which remain the popup/context-menu
widgets.

These are plain data classes, not `Widget` subclasses. This is what makes the
macOS bridge possible: `NSMenu` renders labels, accelerators, and check
marks — not arbitrary widget subtrees.

### 4.2 Item properties

| Property | Type | Notes |
| --- | --- | --- |
| `label` | `str \| ObservableBase[str]` | |
| `on_select` | `VoidCallback` | Zero-argument, sync or async — same contract as `key_shortcut(on_trigger=...)`. |
| `shortcut` | `ShortcutLike \| None` | A spec string (`"Accel+S"`) or `Shortcut`; parsed via `to_shortcut()`. |
| `enabled` | `bool \| ObservableBase[bool]` | Default `True`. |
| `checked` | `Observable[bool] \| None` | Presence makes the item checkable. Must be writable: activation toggles it (Section 5.2). |
| `submenu` | `Sequence[MenuBarItem] \| None` | |

### 4.3 Reactivity contract

- `label`, `enabled`, and `checked` updates propagate live to whichever
  surface is rendering the model — repaint for the in-app bar, `setTitle:` /
  `setEnabled:` / `setState:` calls for `NSMenu`.
- **Structure is not observable.** Adding or removing items (e.g. "Open
  Recent") is done by assigning a new model to `app.menu`, which rebuilds the
  rendered surface wholesale. Menus are small; diffing is not worth its
  complexity. If rebuild cost ever matters on macOS, diffing can be added
  behind the same API.

### 4.4 Standard items

Prebuilt factories on `MenuBarItem` for commands the framework already owns
as built-in intents (`src/nuiitivet/runtime/intents.py`):

- `MenuBarItem.quit()` — dispatches `ExitAppIntent`
- `MenuBarItem.full_screen()` — dispatches `FullScreenIntent`
- `MenuBarItem.minimize()`, `MenuBarItem.maximize()`, ... as needed

Standard items are how built-in commands stay declarative without an
`intent=` parameter. They also absorb platform conventions: labels ("Exit"
vs "Quit ⟨App⟩"), placement (on macOS, `quit()` relocates to the application
menu regardless of where the author put it), and native selectors where macOS
provides them. Labels and shortcuts are overridable.

## 5. Registration and Dispatch

### 5.1 Registration

```python
app = nv.App(
    content=Home,
    title="MyEditor",
    menu=nv.MenuBar([
        nv.MenuBarItem("File", submenu=[
            nv.MenuBarItem("Open...", shortcut="Accel+O", on_select=open_file),
            nv.MenuBarItem("Save", shortcut="Accel+S",
                           on_select=save, enabled=can_save),
            nv.MenuBarItem.separator(),
            nv.MenuBarItem.quit(),
        ]),
    ]),
)
```

`App` gains a `menu: MenuBar | None = None` keyword and a settable
`app.menu` property for wholesale replacement (Section 4.3).

Callbacks needing the `App` (e.g. to dispatch a built-in intent not covered
by a standard item) reference the app object through an ordinary
late-binding closure: `on_select=lambda: app.dispatch(...)` resolves `app`
at activation time, after `App(...)` has been assigned. The model is data
outside the widget tree, so `App.of(context)` does not apply.

### 5.2 Activation

Activating an item, by any route (click, keyboard navigation, accelerator,
native macOS menu):

1. If the item is checkable, the framework toggles `checked` first.
2. `on_select` is invoked (zero arguments; async callbacks are scheduled the
   same way `key_shortcut` handles them).

A disabled item never activates; the in-app bar renders it dimmed and skips
it in traversal, and the bridge mirrors it via `setEnabled:`.

### 5.3 Accelerators and single-fire

The item's `shortcut` is the single source of truth. Per platform, exactly
one mechanism fires:

- **Windows/Linux**: the menu system registers each shortcut with the
  existing shortcut system for as long as its model is the registered one,
  bound to the item so `enabled` gates firing. The bar itself only
  *displays* the accelerator.
- **macOS**: shortcuts become `NSMenuItem` key equivalents, and the native
  menu fires them; the menu system registers **nothing** in the in-app
  shortcut system for these items, so no double-fire is possible.

Registering the same combination independently via `key_shortcut()` is an
authoring error; the shortcut system's existing conflict behavior applies.
Display strings derive from the shared `Shortcut` model, so `MOD_ACCEL`
renders as `⌘` on macOS and `Ctrl` elsewhere.

## 6. Placement

### 6.1 Default

With no explicit placement, `App` inserts the in-app bar at the top of the
content area, below the chrome — for both `OSChrome` and `CustomChrome`.
The bar participates in normal layout; content shrinks accordingly.

### 6.2 Free placement: `MenuBarArea`

`MenuBarArea` is a widget that marks where the registered menu model should
render — e.g. inside a `CustomChrome` header row (VS Code-style):

- If a `MenuBarArea` is mounted, automatic insertion is suppressed and the
  bar renders there instead.
- Mounting a second `MenuBarArea` raises.
- A `MenuBarArea` with no registered menu renders nothing (zero size), so
  conditional menus are allowed.

The model stays on `App` in all cases; `MenuBarArea` moves only the pixels.
Menu definitions, callbacks, and shortcuts are unaffected by placement.

### 6.3 macOS

On macOS neither placement applies: the model goes to the global menu bar,
automatic insertion is disabled, and a mounted `MenuBarArea` collapses to
zero size. A `CustomChrome` header written around a `MenuBarArea` therefore
degrades to a plain title bar on macOS with no platform branching in app
code — which matches the platform convention that menus are not in the
window.

## 7. Platform Rendering

### 7.1 Windows / Linux: in-app bar

- The bar is an internal widget rendering the model's top-level items
  horizontally; its colors come from `MenuBarThemeData` (Section 8).
- Open menus are popups going through the unified overlay anchoring, reusing
  the MD3 `Menu` widget machinery (`src/nuiitivet/material/menu.py`), which
  already provides popup surfaces, keyboard traversal
  (`_MenuTraversalPolicy`), and submenu expansion (`SubMenuItem`). The
  menubar popup is an internal adapter from `MenuBarItem` data to those
  widgets; the MD3 widgets' public API is unchanged, and their colors are
  supplied from the menubar's own palette (Section 8.4).
- Keyboard behavior: `Left`/`Right` move across top-level menus (wrapping),
  `Up`/`Down` traverse items skipping separators and disabled items,
  `Enter` activates, `Escape` closes one level. This follows the existing
  interaction architecture (`docs/design/INTERACTION_ARCHITECTURE.md`).

### 7.2 macOS: `NSMenu` bridge

- Implemented with `pyglet.libs.darwin.cocoapy` (`ObjCClass`,
  `send_message`), which pyglet already bundles and which
  `src/nuiitivet/runtime/app.py` already uses for window management. No new
  dependency; specifically, pyobjc is not added.
- The bridge is a one-way translator: model → `NSMenu` tree on registration
  or replacement; observable property changes → targeted setter calls
  (Section 4.3). Item activation calls back into the same dispatch path as
  the in-app bar (Section 5.2); Cocoa delivers menu actions on the main
  thread, which is the UI thread, so no cross-thread marshalling is needed.
- **Application menu**: macOS requires an application menu (About / Quit).
  The framework synthesizes one from `title` when the author's model does
  not provide it, and relocates a `MenuBarItem.quit()` found elsewhere into
  it. Authors can define the application menu explicitly to take control.
- The bridge target is the pyglet Cocoa window's application; behavior with
  multiple windows follows whatever the App/window model does at that time
  (currently one window per App).

## 8. Styling

### 8.1 Placement in the layer model

The menu bar is not a Material Design component — m3.material.io defines
popup Menus, but no desktop menu bar. Like the scrollbar, it is a generic
framework widget, so its styling follows the scrollbar precedent exactly
(`src/nuiitivet/scrolling/scrollbar_theme_data.py`): the model, style, and
theme-data types live in a framework-common package (`nuiitivet/menubar/`),
not under `material/`, and the palette arrives through the generic
`ThemeExtension` seam rather than by reading Material color roles directly.

### 8.2 `MenuBarThemeData` (app-wide palette)

A `ThemeExtension` that each design system registers into its `Theme`
(`material.theme` and `theme.plain_theme`, as with `ScrollbarThemeData`).
Colors are `ColorSpec` tokens resolved at paint time, so light/dark
switching works automatically. It covers **both surfaces** the menu system
draws:

- **Bar**: background, item foreground, item hover / pressed, the
  highlight of the currently open top-level item, disabled foreground.
- **Popup**: container background, item label, accelerator text, item
  hover / pressed, disabled, divider.

Defaults on a bare `MenuBarThemeData()` are neutral, design-system-agnostic
literals, so the menu bar renders acceptably with no design system
registered. The Material registration expresses its palette in MD3 role
tokens (`SURFACE`, `ON_SURFACE`, ...), which is what makes menubar popups
match MD3 `Menu` widgets under a Material theme.

### 8.3 `MenuBarStyle` (per-instance)

Geometry plus nullable per-instance color overrides, mirroring
`ScrollbarStyle`: bar height, item padding, popup corner radius and
minimum width, and `Optional[ColorSpec]` fields that fall back to the
theme data when `None`. It attaches to the model root — `MenuBar(items,
style=...)` — because the model is always present, whereas `MenuBarArea`
is optional (a style on the area could not be expressed under default
placement).

On macOS neither type applies: the global menu bar is rendered by the OS.

### 8.4 Popup styling flows through the theme data

The in-app popups reuse the MD3 `Menu` widget machinery (Section 7.1), but
their colors come from `MenuBarThemeData`, not from the MD3 menu defaults:
`MenuStyle`'s color fields are plain `ColorSpec`, so the menubar adapter
builds the internal `MenuStyle` from the theme data (and any
`MenuBarStyle` overrides) and passes it in. The MD3 widgets are unchanged;
under a Material theme the derived style reproduces the MD3 menu look
because the registered palette uses the same role tokens. The alternative —
letting popups fall back to MD3 menu theming directly — was rejected
because it would leave a non-Material design system with Material-colored
popups under a framework-common bar.

## 9. Rejected Alternatives

### 9.1 `MenuBar` as a widget in the tree

Rejected because the macOS global bar is outside the window: a tree-resident
widget would need to "teleport" its subtree out of the window on one
platform, and would invite arbitrary child widgets that `NSMenu` cannot
render. Frameworks that split the API by platform instead (Flutter's
`PlatformMenuBar` vs `MenuBar`, Avalonia's `NativeMenu` vs `Menu`) force app
authors to write menus twice; Qt and Electron's single-model approach is the
pattern followed here.

### 9.2 An `intent=` parameter on items

Rejected for the reasons in Section 3 (decision 2): with `App.dispatch`
closed over built-in intents, `intent=` adds a second authoring path whose
entire benefit is replicating what standard items already do, while creating
pressure to add `intent=` to every interactive widget. If a user-extensible
command system ever exists, this decision should be revisited there, not
here.

### 9.3 Deriving accelerators from independently registered shortcuts

The issue that motivated this design asked whether items should *look up*
their accelerator from shortcuts registered elsewhere. Rejected in favor of
declaring the shortcut on the item and letting the menu system register it:
lookup would make menu construction order-dependent on modifier
registration, and the drift it prevents is prevented equally well by having
exactly one declaration site.

## 10. Staging

1. **Stage 1 — model + in-app bar**: `MenuBar` / `MenuBarItem`,
   `App(menu=...)`, default placement, `MenuBarArea`, observable property
   propagation, shortcut registration and display, keyboard navigation,
   standard items dispatching built-in intents, and styling
   (`MenuBarThemeData` registrations, `MenuBarStyle`, popup style
   derivation — Section 8). macOS renders the same in-app bar temporarily.
2. **Stage 2 — macOS bridge**: `NSMenu` translation, application-menu
   synthesis, standard-item relocation and native selectors, `MenuBarArea`
   collapse on macOS.

The API is identical across stages; Stage 2 changes only where pixels come
from on macOS. Shipping Stage 1 alone leaves macOS with an in-window bar,
which is visibly non-native — acceptable for a development window, and the
reason Stage 2 should follow closely.

## 11. Open Questions

- Naming of `MenuBarArea` (`MenuBarSlot` and `MenuBarView` were the
  alternatives considered).
- Whether Stage 1 should hide the bar on macOS instead of showing the
  non-native in-window bar.
- The exact set of standard items beyond `quit()` / `full_screen()`, and
  whether an Edit-menu set (Cut/Copy/Paste wired to text editing) is worth
  providing before the macOS bridge exists.
