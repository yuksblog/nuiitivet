# Menu Bar Design

## 1. Purpose and Scope

This document defines the design of the application menu bar: the declarative
menu model registered on `Window`, its rendering on Windows/Linux as an in-app
widget, and its bridging to the global menu bar (`NSMenu`) on macOS.

### In scope

- The menu model (`MenuBar`, `MenuBarItem`) and its reactivity contract
- Registration on `Window` and activation dispatch
- Placement rules, including free placement inside a `CustomChrome`
- Platform split: in-app rendering vs. the macOS `NSMenu` bridge
- Integration with the keyboard-shortcut system
  (`docs/design/KEYBOARD_SHORTCUTS.md`)
- Styling: the theme-extension palette and per-instance style (Section 8)

### Out of scope

- Context menus and dropdown menus attached to widgets — those are the
  existing MD3 `Menu` / `MenuItem` widgets (`src/nuiitivet/material/menu.py`)
- Tray icons and other desktop integration
- A general user-extensible command/intent system

## 2. Terminology

- **menu model**: The plain declarative data tree (`MenuBar` and its items)
  registered on `Window`. Not widgets.
- **in-app bar**: The Nuiitivet-drawn horizontal bar rendering the menu model
  on Windows/Linux.
- **global menu bar**: The macOS system menu bar at the top of the screen,
  driven through `NSMenu`.
- **standard item**: A prebuilt `MenuBarItem` factory (e.g. `quit()`) whose
  behavior and per-platform placement the framework owns.
- **accelerator**: The keyboard shortcut displayed next to an item and able to
  activate it while the menu is closed.

## 3. Design Decisions

1. **The menu is a model registered on `Window`, not a widget in the tree.**
   On macOS the menu lives outside the window, so a widget-tree API cannot be
   truthful on both platforms. `Window(menu=...)` sits beside `title=` and
   `chrome=`.
2. **One activation path: `on_select` callbacks.** Built-in commands are
   covered by standard items (Section 4.4); there is no `intent=` parameter.
3. **Item properties are `Observable`-bindable**, following the `title=`
   precedent on `Window`. Structural changes are wholesale replacement, not
   diffing (Section 4.3).
4. **Accelerators are declared on the item and registered by the menu
   system.** One definition drives display, activation, and per-platform
   presentation (`⌘S` vs `Ctrl+S`). Declaring the same shortcut both on a
   menu item and via `key_shortcut()` is an authoring error.
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

- `MenuBar(items: Sequence[MenuBarItem], *, style: MenuBarStyle | None)` —
  the root.
- `MenuBarItem` — a single entry. One type covers all roles:
  - **Action**: `MenuBarItem(label, on_select=..., shortcut=..., enabled=...,
    checked=...)`
  - **Submenu**: `MenuBarItem(label, submenu=[...])` — top-level bar entries
    ("File", "Edit") are simply items with a `submenu`. Nesting is unlimited.
  - **Separator**: `MenuBarItem.separator()`.

Construction-time validation: a non-separator item must have exactly one of
`on_select`, `submenu`, or a standard-item role, and `submenu` is mutually
exclusive with `shortcut` / `checked`. Violations raise immediately, not at
render time.

The names avoid colliding with the MD3 widgets `Menu` / `MenuItem`
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
  Recent") is done by assigning a new model to `window.menu`, which rebuilds the
  rendered surface wholesale.

### 4.4 Standard items

Prebuilt factories on `MenuBarItem` carrying a role
(`MenuBarRole`); activation dispatches the mapped built-in intent
(`src/nuiitivet/runtime/intents.py`) on every platform, so window management
and app exit stay on the one dispatch path:

- `MenuBarItem.quit()` → `ExitAppIntent`
- `MenuBarItem.close_window()` → `CloseWindowIntent`
- `MenuBarItem.minimize()` → `MinimizeWindowIntent`
- `MenuBarItem.maximize()` → `MaximizeWindowIntent`
- `MenuBarItem.restore()` → `RestoreWindowIntent` — the way back from
  `full_screen()` / `maximize()` / `minimize()`; `FullScreenIntent` itself
  only enters full screen
- `MenuBarItem.full_screen()` → `FullScreenIntent`

Standard items absorb platform conventions: labels ("Exit" vs "Quit",
"Maximize" vs "Zoom"), default accelerators (⌘Q / ⌘W / ⌘M on macOS), and
placement (on macOS, `quit()` relocates to the application menu — Section
7.2). Labels, shortcuts, and `enabled` are overridable per factory call.

## 5. Registration and Dispatch

### 5.1 Registration

```python
app = nv.App(
    nv.Window(
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
    ),
)
```

`Window` takes a `menu: MenuBar | None = None` keyword and a settable
`window.menu` property for wholesale replacement (Section 4.3). Per
window, a `MenuBarController` (`nuiitivet/menubar/controller.py`) owns the
registered model, the rendering surfaces, and the shared activation path.

Callbacks needing the window or the app (e.g. to dispatch a built-in
intent not covered by a standard item) reference the object through an
ordinary late-binding closure: `on_select=lambda: window.dispatch(...)`
resolves `window` at activation time. The model is data outside the
widget tree, so `.of(context)` does not apply.

### 5.2 Activation

Every route (click, keyboard navigation, accelerator, native macOS menu)
funnels into `MenuBarController.activate(item)`:

1. If the item is checkable, `checked` is toggled first.
2. A standard item dispatches its role's built-in intent; otherwise
   `on_select` is invoked (zero arguments; async callbacks are scheduled the
   same way `key_shortcut` handles them).

A disabled item never activates; the in-app bar renders it dimmed and skips
it in traversal, and the bridge mirrors it via `setEnabled:`.

### 5.3 Accelerators and single-fire

The item's `shortcut` is the single source of truth. Per platform, exactly
one mechanism fires:

- **Windows/Linux**: the bar widget registers each shortcut with the
  shortcut system (`ShortcutScope.MOUNT`, live while the bar is mounted),
  bound to the item so `enabled` gates firing. The bar itself only
  *displays* the accelerator (via `Shortcut.display`).
- **macOS**: shortcuts become `NSMenuItem` key equivalents and the native
  menu fires them. The in-app bar does not render there (Section 6.3), so
  its bindings never register and no double-fire is possible.

Registering the same combination independently via `key_shortcut()` is an
authoring error; the shortcut system's existing conflict behavior applies.
Display strings derive from the shared `Shortcut` model, so `MOD_ACCEL`
renders as `⌘` on macOS and `Ctrl` elsewhere.

## 6. Placement

### 6.1 Default

With no explicit placement, the `Window` inserts the in-app bar at the top of the
content area, below the chrome — for both `OSChrome` and `CustomChrome`.
The bar participates in normal layout; content shrinks accordingly. The
default slot is inserted only when a menu is registered at `Window`
construction; a menu-less window carries no extra widgets.

### 6.2 Free placement: `MenuBarArea`

`MenuBarArea` is a widget that marks where the registered menu model should
render — e.g. inside a `CustomChrome` header row:

- If a `MenuBarArea` is mounted, automatic insertion is suppressed and the
  bar renders there instead.
- With several mounted `MenuBarArea` widgets, the first renders and the
  rest are inert (logged once); raising would break the mount of an
  otherwise valid tree, and hot reload with it.
- A `MenuBarArea` with no registered menu renders nothing (zero size), so
  conditional menus are allowed.

The model stays on `Window` in all cases; `MenuBarArea` moves only the pixels.
Menu definitions, callbacks, and shortcuts are unaffected by placement.

### 6.3 macOS

On macOS neither placement applies: the model goes to the global menu bar,
automatic insertion yields a zero-size slot, and a mounted `MenuBarArea`
collapses to zero size. A `CustomChrome` header written around a
`MenuBarArea` therefore degrades to a plain title bar on macOS with no
platform branching in app code.

## 7. Platform Rendering

### 7.1 Windows / Linux: in-app bar

- The bar is an internal widget (`nuiitivet/menubar/bar.py`) rendering the
  model's top-level items horizontally; its colors come from
  `MenuBarThemeData` (Section 8).
- Open menus are popups going through the unified overlay anchoring, reusing
  the MD3 `Menu` widget machinery (`src/nuiitivet/material/menu.py`) —
  popup surfaces, keyboard traversal, submenu expansion — through an
  internal adapter from `MenuBarItem` data to those widgets. The MD3
  widgets' public API is unchanged; their colors are supplied from the
  menubar's own palette (Section 8.4).
- Keyboard behavior: `Left`/`Right` move across top-level menus (wrapping),
  `Up`/`Down` traverse items skipping separators and disabled items,
  `Enter` activates, `Escape` closes one level. This follows the existing
  interaction architecture (`docs/design/INTERACTION_ARCHITECTURE.md`).
- Two contracts with the overlay: the popup treats an unmount as a
  dismissal only when its entry's result is settled (`OverlayHandle.done()`)
  — the overlay remounts live entries whenever its stack changes — and it
  restores its focused row across such transient remounts, which would
  otherwise drop the keyboard focus.

### 7.2 macOS: `NSMenu` bridge

- `nuiitivet/menubar/nsmenu.py`, in two halves: a **pure translation**
  (`key_equivalent` — `Shortcut` → `NSMenuItem` key equivalent and modifier
  mask; `plan_menus` — application-menu synthesis and item arrangement)
  that imports and tests on every platform, and a **Cocoa layer**
  (`NSMenuBridge`) built on `pyglet.libs.darwin.cocoapy` (`ObjCClass`,
  `ObjCSubclass`), imported lazily and only on macOS. No new dependency;
  specifically, pyobjc is not added.
- The controller installs the bridge when the backend window exists
  (`Window._on_window_created`, called by the pyglet runner). While the bridge
  is installed, `active_slot()` is `None` and every in-app slot collapses.
- The bridge is a one-way translator: model → `NSMenu` tree on registration
  or replacement; observable property changes → targeted setter calls
  (Section 4.3), applied on the next clock tick so off-thread writes land
  on the UI thread. Item activation calls
  `MenuBarController.activate` (Section 5.2); Cocoa delivers menu actions
  on the main thread, which is the UI thread, so no marshalling is needed.
- **Application menu**: the first menu is always the application menu. A
  `quit()` standard item found as a direct child of a top-level menu is
  relocated into it (dangling separators are cleaned up); when the model
  has none, one is synthesized. A top-level action item (no submenu)
  degrades to a menu holding that single entry, since the global bar has no
  direct-action titles.

## 8. Styling

### 8.1 Placement in the layer model

The menu bar is not a Material Design component — m3.material.io defines
popup Menus, but no desktop menu bar. Like the scrollbar, it is a generic
framework widget, so its styling follows the scrollbar precedent
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

- **Bar**: background, item foreground, hover/press state layer, the
  highlight of the currently open top-level item, disabled foreground.
- **Popup**: container background, item label, accelerator text, state
  layer, disabled, divider.

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
`MenuBarStyle` overrides) and passes it in. The MD3 widgets are unchanged,
and a non-Material design system gets popups in its own palette rather
than Material's.
