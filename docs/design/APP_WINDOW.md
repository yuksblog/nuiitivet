# App / Window Separation Design

## 1. Purpose and Scope

This document defines the separation of "the application" from "a window":
`Window` as a public type, opening and closing secondary windows from a
running app, parent/child relationships, the application exit policy, and
what every formerly window-scoped concept on `App` means once there can be
more than one window.

### In scope

- The `App` / `Window` split and the `App(Window(content=...))` shape
- The `Window` lifecycle: construct → `open()` → `close()`
- Parent/child windows and framework-level modality
- The exit policy (`ExitPolicy`)
- Intent scoping: which intents dispatch through `App` and which through
  `Window`
- Per-window resolution of `.of(context)` services: `Overlay`, `Navigator`,
  focus, shortcuts, IME, menu bar
- Hot reload and dev-bridge addressing across windows

### Out of scope (deliberate future seats)

- `hide()` / `show()` visibility toggling — `close()` destroys; a
  hide/show verb pair can be added later without changing `close()`
- Per-window theme override (`Window(theme=...)`) — the parameter's
  semantics are defined here (Section 8.5) but not implemented initially
- Close-request veto (e.g. "unsaved changes" interception)
- OS-native modality and OS-native parent/child stacking (Section 6.3)
- Opening several windows from one `Window` object (one object is one
  window; construct another `Window` for another window)

## 2. Terminology

- **App**: The process-wide runtime — the event loop (`run()`), the theme
  source, the app-scoped intent dispatcher, and the registry of windows.
  Owns no pixels of its own.
- **Window**: A public object representing exactly one OS window and its
  widget tree, overlay, navigator, focus state, and menu bar.
- **main window**: The window that defines the app's identity for the
  `MAIN_WINDOW_CLOSED` exit policy: the one passed to the `App`
  constructor.
- **parent / child**: A structural relation declared at `Window`
  construction. Closing a parent closes its children.
- **framework modal**: Modality implemented by nuiitivet (input to the
  parent chain is blocked while a modal child is open), as opposed to OS
  modality, which the backend does not provide (Section 6.3).

## 3. Design Decisions

1. **`Window` is imperative, not declarative.** Windows are opened and
   closed by verbs on objects, like `Navigator.of(context).push(...)` and
   overlay handles — not declared as a function of state (SwiftUI /
   Compose scenes). Windows cannot be children in a layout tree, so a
   widget-tree API could not be truthful.
2. **One object, one window lifetime.** The constructor builds a model
   (no OS window yet); `open()` realizes it; `close()` destroys it. A
   closed `Window` is finished — to show the same content again,
   construct a new `Window`. State that must survive a window lives in
   app-layer `Observable`s passed into the content, which is the
   framework's existing state idiom. This is the mainstream semantics
   (Electron, WPF, WinForms); Qt's close-hides is the outlier.
3. **`App` takes its main window; there is no sugar constructor.**
   `App(Window(content=...))` is the only shape: `App` accepts a
   ready-made `Window` plus the app-level options (`theme`,
   `exit_policy`), and every window-flavored keyword lives on `Window`
   (Section 5.1). `App` itself keeps only `run()`, `theme`,
   `exit_policy`, and app-scoped dispatch.
4. **Parent and modality are construction-time options** —
   `Window(parent=..., modal=True)`, following Qt / Electron / Tk. Modality
   is framework modal (Section 6.3).
5. **Exit is a three-valued policy**, `ExitPolicy`, defaulting to
   `LAST_WINDOW_CLOSED` (Section 6.4).
6. **The menu bar moves to `Window`.** Its rendering is already
   per-window (`docs/design/MENU_BAR.md`); `Window(menu=...)` declares
   it, on the main window like any other.
7. **Intent dispatch is scoped by entry point.** Window intents dispatch
   via `Window.of(context).dispatch(...)`, app intents via
   `App.of(context).dispatch(...)`. A scope mismatch raises — it is never
   silently ignored (Section 7). Reading the call site reveals where an
   intent lands; that explicitness is the point.
8. **The theme is app-wide.** `App(..., theme=...)` supplies every
   window. `Window(theme=...)` is the reserved override seat
   (Section 8.5).
9. **`.of(context)` resolves through the window the context belongs to.**
   Each window's root is wrapped in a window scope; `Overlay.of` /
   `Navigator.of` (including their fallback for contexts whose tree lookup
   fails) resolve to the services of that window, never to a process-wide
   default (Section 8.1).

## 4. The `Window` Type

### 4.1 Construction

```python
palette = nv.Window(
    content=ToolPalette,            # Widget or zero-arg root factory
    width=280, height=480,          # WindowSizingLike, "auto" supported
    title="Tools",                  # str | Observable, as on App today
    chrome=nv.OSChrome(),
    background=...,
    resizable=True,
    window_position=None,
    overlay_factory=None,
    menu=None,                      # MenuBar model (Section 8.4)
    parent=None,                    # Window | None
    modal=False,                    # requires parent
)
```

Construction builds a model only: no OS window, no mounted tree, no
registration. Every window-flavored keyword formerly on `App` moves here
with unchanged meaning; `content` keeps the App contract (a `Widget`
instance or a root factory; the factory form is what enables hot reload,
Section 9.1). `modal=True` without `parent` raises at construction.

### 4.2 Lifecycle

- `open() -> Window`: realizes the OS window, builds and mounts the tree
  (root factory → implicit or explicit `Navigator` → overlay stack, the
  same composition `App` performs today), and registers the window with
  the running `App`. Returns `self`. Calling `open()` before `app.run()`
  is allowed; such windows are realized when the loop starts. Opening an
  already-open or already-closed window raises.
- `close() -> None`: unmounts the tree, destroys the OS window, and
  unregisters. Closing an unopened or already-closed window is a no-op.
  Children close first (Section 6.2).
- `closed`: an awaitable that resolves when the window has closed —
  whether via `close()`, the OS close button, `CloseWindowIntent`, or a
  parent closing.
- `is_open`: an `ObservableBase[bool]`.

The OS close button and `CloseWindowIntent` are equivalent to `close()`.

### 4.3 Operations

The window-manipulation verbs currently buried in `App.dispatch` become
imperative methods: `maximize()`, `minimize()`, `restore()`,
`full_screen()`, `center()`, `move_to(x, y)`, `resize(w, h)`, plus the
`title` property (Observable-bindable) and `menu` property (wholesale
replacement, as `app.menu` today). The corresponding intents (Section 7)
are thin declarative wrappers over these methods for menu items and
accelerators; both paths funnel into the same implementation.

### 4.4 `Window.of(context)`

Returns the `Window` whose tree contains `context`, following the
established `.of()` convention — including its timing rule: valid from
`on_mount`, not from `__init__`. There is no proxy type; the returned
object is the same `Window` the opener holds.

## 5. The `App`

### 5.1 Construction

```python
app = nv.App(
    nv.Window(content=Home, title="Main", width=800, height=600, menu=...),
    theme=...,
    exit_policy=...,
)
```

`App` takes its main `Window` as the first argument, plus the app-level
options `theme` and `exit_policy` — nothing else. There is no sugar form
that accepts window keywords on `App`: the signature is the scope split
(Section 7) made visible, and a forwarding constructor would have to
mirror every future `Window` parameter forever. Passing anything but a
`Window` first raises with the wrapping hint. `run()` opens the main
window (and any other windows on which `open()` was already called),
runs the loop, and returns when the exit policy says so (Section 6.4).

### 5.2 Surface

`App` keeps: `run()`, `theme`, `exit_policy`, `App.of(context)` (still
returning the dispatch-only `AppProxy`, whose handled set shrinks to the
app-scoped intents, Section 7), and gains `main_window` and `windows`
(a snapshot tuple of currently open windows). Window-flavored properties
on `App` (`title`, `menu`, `width`, ...) are removed — callers go through
`app.main_window`. One deliberate exception: `App.render_to_png(path)`
stays, delegating to the main window, because it is the headless
counterpart of `run()` — "render the app" is an app-level sentence, and
it is the operation every sample's docs harness performs. Breaking
changes are acceptable per project policy.

## 6. Windows at Runtime

### 6.1 Opening from app code

```python
class Screen(nv.ComposableWidget):
    def _open_palette(self) -> None:
        self._palette = nv.Window(
            content=ToolPalette,
            title="Tools",
            parent=nv.Window.of(self),
        ).open()
```

There is no `OpenWindowIntent`: opening needs content and configuration,
which is an imperative concern. A "New Window" menu item simply calls
this from `on_select`.

### 6.2 Parent / child

- A child stacks above its parent and follows it in minimize/restore,
  best-effort per platform (Section 6.3).
- Closing a window closes its children first, transitively.
- `modal=True`: while the child is open, the parent chain receives no
  pointer or keyboard input — the same barrier idea as a modal overlay,
  applied across windows. Sibling top-level windows are unaffected
  (window-modal, not app-modal).

### 6.3 Platform reality

pyglet supports multiple windows natively, which is all that plain
multi-window needs. It does **not** expose parent/child stacking,
modality, or keep-above cross-platform. Therefore:

- Modality is enforced by nuiitivet (input blocking in the event path),
  not by the OS. The OS may still allow the parent to be raised above the
  modal child; the framework re-raises the child on parent activation,
  best-effort.
- Stacking/minimize-follow uses per-platform code where available (the
  IME precedent: platform-specific modules behind one interface), and
  degrades gracefully where not.

### 6.4 Exit policy

```python
class ExitPolicy(Enum):
    LAST_WINDOW_CLOSED = ...   # default: run() returns when no window remains
    MAIN_WINDOW_CLOSED = ...   # closing the main window closes all windows and exits
    EXPLICIT = ...             # run() returns only on ExitAppIntent
```

`App(..., exit_policy=...)`. Under every policy `ExitAppIntent` closes all
windows (children before parents) and exits with its `exit_code`. Under
`EXPLICIT`, an app with zero open windows keeps running — the policy for
tray-style or macOS-conventional apps; some window must be reopenable
from app-held state (a menu callback, a timer, an outside event).

## 7. Intent Scoping

Two dispatch entry points, split by what the intent is about:

| Scope | Entry | Intents |
| --- | --- | --- |
| App | `App.of(context).dispatch(...)` | `ExitAppIntent`, `ThemeModeIntent`, `ThemeRegistryIntent` |
| Window | `Window.of(context).dispatch(...)` | `CloseWindowIntent`, `CenterWindowIntent`, `MaximizeWindowIntent`, `MinimizeWindowIntent`, `RestoreWindowIntent`, `FullScreenIntent`, `MoveWindowIntent`, `ResizeWindowIntent` |

- A window intent addresses the window it was dispatched through —
  `Window.of(context)` pins the target to the context's own window.
- **Scope mismatch raises** (`TypeError`); it is reported through the
  standard swallowed-callback path when it happens inside a callback.
  Silent misdelivery would defeat the readability that motivates the
  split.
- Dialog intents are unaffected: `Overlay.of(context).dialog(intent)` is
  an established `Overlay`-scoped path with its own `IntentResolver` and
  never passed through `App.dispatch`. Per-window overlays make it
  window-correct automatically.
- Menu-bar standard items (`MenuBarItem.quit()`,
  `MenuBarItem.close_window()`, ...) keep dispatching their mapped
  intents; each menu bar belongs to a window, so its controller
  dispatches window intents through that window and app intents through
  the app.
- Module placement: the window intents move from
  `nuiitivet/runtime/intents.py` to `nuiitivet/runtime/window_intents.py`
  beside the new `nuiitivet/runtime/window.py`; `ExitAppIntent` stays.
  The public surface (`nv.CloseWindowIntent`, ...) is unchanged.

## 8. Window-Scoped Services

### 8.1 `.of(context)` resolution

Each window's root is wrapped in an internal window scope (the analogue
of today's `AppScope`, which remains app-wide and carries the theme).
`Overlay.of(context)` and `Navigator.of(context)` resolve within the
context's window; their existing fallback (used because the overlay
stack is a sibling of the content, not an ancestor) consults the
context's window scope — not a process-wide App default, which would
silently cross windows. The `on_mount` timing rule is unchanged.

### 8.2 Overlay and Navigator

One overlay stack and one root navigator per window, built by
`Window.open()` exactly as `App.__init__` builds them today
(`overlay_factory` moves along). Dialogs, menus, and tooltips are
confined to their window, as before — that confinement is precisely why
secondary windows exist.

### 8.3 Focus, keyboard, shortcuts

- Each window keeps its own focus state; the OS decides which window is
  focused and key events enter that window's tree only.
- Shortcut bindings are tree-anchored (`FOCUS` / `FOREGROUND` / `MOUNT`,
  `docs/design/KEYBOARD_SHORTCUTS.md`), so they are naturally per-window:
  a `MOUNT`-scoped binding fires only for key events delivered to its own
  window. There is still no `APPLICATION` scope; a command that must work
  from every window is registered in each window's tree (typically via a
  shared content-root modifier), or is a menu accelerator on each
  window's menu.

### 8.4 Menu bar

`menu=` moves to `Window`; the main window declares its menu the same
way every window does. On Windows/Linux each window renders its own in-app bar —
already per-window in the current design. On macOS the global bar
follows the focused window (the AppKit convention): the `NSMenu` bridge
installs the focused window's model, and a window with `menu=None` shows
the main window's menu, so single-menu apps keep today's behavior
without per-window declarations. *Implementation status*: the initial
multi-window release installs only the main window's menu on the global
bar (secondary-window menus render nowhere on macOS); the focused-window
switch is a follow-up, since swapping `NSMenu` ownership on focus is its
own piece of Cocoa work.

### 8.5 Theme

`App(..., theme=...)` is the single theme source; every window's tree reads
it through the app-wide scope. `Window(theme=...)` is reserved: when
implemented, a window-local theme shadows the app theme for that window's
tree only, and `ThemeModeIntent` / `ThemeRegistryIntent` remain
app-scoped.

### 8.6 IME

The process-wide `IMEManager` singleton (one cursor rect, one window
location) is re-keyed per window: composition state, cursor tracking, and
window location become per-window, owned by the window's platform half
and switched with OS focus. The platform-module split is unchanged.
*Implementation status*: the platform IME patch installs per OS window,
and the singleton's window geometry is published only by the OS-focused
window (a single-window app keeps publishing unconditionally). The cursor
rect already follows the focused text field, which lives in the focused
window; a fully per-window manager remains follow-up work.

## 9. Tooling

### 9.1 Hot reload

Each `Window` holds its own root factory. A module reload rebuilds the
tree of every open window through its factory, under the existing
rebuild/commit path. Closed windows stay closed — a reload never
resurrects a window; the constructing code path must run again.

### 9.2 Dev bridge

The bridge tools currently assume one tree. They gain an optional window
selector: `status` lists open windows (id, title, main/focused flags),
and tree/state/action tools accept `window=<id>` defaulting to the main
window — a deterministic default for agent use, since agent-launched
apps do not reliably hold OS focus. Actions targeting a window blocked
by a modal child fail loudly, consistent with the bridge's
covered-target behavior.

## 10. Internal Design

### 10.1 Ownership

- `runtime/window.py` — `Window` implements the entire host protocol
  that widget trees mount against: layout, invalidation and redraw
  scheduling, focus and interaction state, input dispatch, overlay and
  navigator construction, menu bar, and lifecycle. `WindowScope` lives
  beside it.
- `runtime/app.py` — `App` owns the window registry, the
  `ThemeManager`, `run()` (the event-loop handoff), `ExitPolicy`
  evaluation, and app-scoped dispatch. `AppScope` and `AppProxy` live
  here.
- `backends/pyglet/runner.py` — `run_app(app)` owns process-wide setup
  and the loop; `_realize_window(owner_app, win, ...)` turns one open
  `Window` into an OS window (pyglet window, event wiring, per-window
  GPU state, IME patch). Windows opened before `run()` are realized at
  loop start; windows opened while running are realized through the
  app's realize hook, which registration triggers.

### 10.2 Structure and flow

Every open window's mounted tree is
`AppScope(app) > WindowScope(window) > root`; each `.of(context)`
lookup stops at the nearest matching scope, so app-wide lookups succeed
from any window while window-scoped ones never cross windows.

`open()` builds and mounts the tree, then registers with the app.
`close()` closes children first, unmounts, destroys the OS window, and
unregisters; unregistration is where the exit policy fires.

### 10.3 Invariants

- Nothing below the host protocol knows which window hosts it. Widget
  code is window-agnostic; multi-window concerns end at `Window`.
- Scope widgets are passive carriers: they make `App` and `Window`
  findable from a context and do nothing else.
- Theme-change propagation is owned by `App`: it subscribes to the
  `ThemeManager` once and fans out invalidation to every open window.
  Scopes wire no callbacks.
- A window blocked by a modal child consumes keyboard input and drops
  pointer input; the gates sit in the window's `_dispatch_*` methods,
  below every OS event path. Synthetic actions (dev bridge) do not rely
  on the silent gates — they raise, naming the blocking window.
- Window ids are process-monotonic and never reused; an id is stable
  for the window's lifetime, including across hot reloads.
- Lifecycle state only moves forward (created → open → closed); one
  `Window` object corresponds to at most one OS window, ever.
