# Tray Icon Design

## 1. Purpose and Scope

This document defines the design of the system tray icon (`TrayIcon`): the
declarative model registered on `App`, the window-visibility primitives that
make a tray-resident app possible (`Window.hide()` / `show()`,
`close_action`), and the per-platform backends.

### In scope

- The `TrayIcon` model and its lifetime contract
- The lifecycle principles: how the tray relates to `ExitPolicy` and the
  close button
- Window visibility as an axis orthogonal to the window lifecycle
- Platform split: direct `NSStatusItem` on macOS vs. pystray elsewhere, and
  Linux's best-effort contract
- macOS Dock presence (`dock_visibility`)

### Out of scope

- Desktop notifications (`Desktop.notify`) and other shell services
- The menu model itself — the tray reuses the menu bar's model; see
  `docs/design/MENU_BAR.md`
- Global hotkeys and other summon mechanisms beyond the tray

## 2. Terminology

- **tray**: The OS surface hosting small always-available app icons — the
  right side of the macOS menu bar (a *menu-bar extra*), the Windows
  notification area, the Linux status area (SNI/AppIndicator).
- **resident app**: An app that keeps running with no visible window and is
  summoned back from the tray (sync clients, monitors, background
  utilities).
- **close-to-tray**: The resident convention for the OS close button: the
  window hides instead of closing.
- **installed**: A `TrayIcon` whose icon is actually showing in the tray —
  as opposed to merely registered on the App.
- **surface**: Anything through which the user can reach the app: a visible
  window, or an installed tray icon.

## 3. Design Decisions

1. **The tray icon is a model registered on `App`, not a widget.** It must
   exist while no window does, so a widget-tree API cannot be truthful.
   `App(tray=...)` sits beside `exit_policy=`, mirroring `Window(menu=...)`.
2. **The tray menu reuses `MenuBarItem`.** One declarative menu model serves
   every native menu surface; Observable `label` / `enabled` / `checked`
   flow through the same live-sync machinery. Window-scoped standard items
   have no target window in a tray menu and are ignored with a warning;
   `quit()` (app-scoped) works. `shortcut` is not rendered — tray menus have
   no accelerator convention.
3. **The tray icon lives exactly as long as the app runs.** Installed when
   the loop starts, removed when it stops. It has no lifetime condition, no
   policy, and no independent teardown of its own.
4. **`ExitPolicy` is untouched and counts existing windows — hidden ones
   included.** The tray never suspends or alters exit behavior. A resident
   app declares `ExitPolicy.EXPLICIT`, the one place app lifetime is already
   decided. (A rejected earlier design suspended window-based exit while a
   tray was installed; the hidden coupling made behavior unpredictable from
   the call site.)
5. **The close button's meaning is a `Window` property:**
   `close_action="close" | "hide"`, Observable-capable. Not `on_close` — the
   `on_*` prefix is the callback convention, and this is a policy value.
   Programmatic `close()` is never remapped. There is no
   `close_to_tray=True` sugar on the tray: a flag that silently rewires a
   different object's behavior is unreadable magic.
6. **No automatic fallback; dangerous states warn instead.** Hiding the last
   visible window with no tray showing logs a one-time warning and behaves
   as written. The framework's job is to make the state knowable
   (`TrayIcon.installed`, an `Observable[bool]`); adapting is the app's job.
   The resident recipe binds
   `close_action=tray.installed.map(lambda ok: "hide" if ok else "close")`,
   making the coupling one visible line of app code. This matches the
   Qt/Electron division of responsibility.
7. **Install failure never takes the app down** (the `Desktop.notify`
   policy: log once, stay up). An app that treats the tray as essential
   reads `installed` and fails fast itself.
8. **`installed` means "the user can reach the app through the tray".** On a
   backend that cannot show a menu at all (pystray's bare-XOrg backend), a
   menu-carrying tray refuses to install rather than reporting an icon the
   user cannot operate — which would steer the resident recipe toward
   locking the user out.
9. **Visibility is an axis orthogonal to the window lifecycle.** The
   lifecycle stays one-way (created → open → closed); `hide()` / `show()`
   toggle visibility of an *open* window whose tree, state, and geometry
   survive. A hidden window renders no frames and still counts for the exit
   policy.
10. **macOS Dock presence is a tray-scoped policy** (`dock_visibility`),
    because the Dock icon belongs to the app, not to a window — unlike the
    Windows/Linux taskbar entry, which follows window visibility by itself
    and needs no knob.

## 4. The `TrayIcon` Model

```python
tray = nv.TrayIcon(
    icon="assets/trayTemplate.png",   # optional; macOS *Template = template image
    tooltip="My Sync App",            # str | Observable[str]
    menu=[MenuBarItem(...), ...],     # the menu bar's model, reused
    on_activate=...,                  # platform-conventional icon activation
    dock_visibility="always",         # "always" | "auto" | "never"; macOS only
)
app = nv.App(window, tray=tray)
```

- `installed: Observable[bool]` — the adaptation seam (Decisions 6–8).
- `on_activate` support varies by platform and is an optional shortcut, not
  a primary affordance: macOS delivers it only without a menu (a menu owns
  the click); Windows on double-click; a Linux AppIndicator host cannot
  deliver it at all. An equivalent menu entry must always exist.
- Activation dispatch mirrors `MenuBarController.activate` minus the window
  scope: toggle `checked`, dispatch `QUIT` through the App, run
  `on_select` — always on the UI thread (the backends guarantee the hop).

## 5. Window Visibility and `close_action`

- `Window.hide()` parks the open window: the OS window disappears (and the
  Windows/Linux taskbar entry with it), the widget tree and geometry stay
  alive, no frames are produced. `Window.show()` restores it, focused; on an
  already-visible window it acts as "summon" (raise + refocus).
  `window.is_visible` is the matching read-only Observable, and
  `HideWindowIntent` / `ShowWindowIntent` are the intent counterparts.
- Hiding **before** the backend realizes the OS window records the desired
  state and the OS window is created invisible — the start-in-tray launch
  shape, with no flash.
- The OS close button is the only remapped path: the backend routes it to
  `Window._handle_close_request()`, which reads `close_action` and either
  closes or hides. `CloseWindowIntent`, menu roles, and `close()` always
  really close.

The resident-app recipe is therefore three independent declarations —
`ExitPolicy.EXPLICIT`, `close_action` bound to `tray.installed`, and the
`TrayIcon` itself — each meaningful without the others. See
`docs/guide/window/tray_icon.md`.

## 6. Platform Backends

The model is backend-agnostic; `TrayIcon._create_bridge()` picks per
platform. The tray menu renders natively everywhere (it must work with no
window on screen), unlike the menu bar's in-app fallback.

### macOS: direct `NSStatusItem` (`tray_cocoa.py`)

Talks to AppKit through pyglet's bundled cocoapy, exactly like the menu
bar's `NSMenu` bridge — no dependency, no extra thread, and the pumped event
loop hosts it unchanged (verified by
`scripts/investigation/spike_tray_nsstatusitem.py`). `NSMenuBuilder`
(extracted from the menu-bar bridge) builds the menu, so both native
surfaces share construction, the ObjC action target, and live Observable
sync. Cocoa delivers actions on the main thread; no marshalling. Menu
tracking pauses painting (Cocoa's modal tracking loop) — identical to the
global menu bar, and accepted.

pystray was rejected on macOS: it wants to own `NSApplication`, and the
direct route removes the only structural risk (handing part of the main
loop to an outside library).

### Windows / Linux: pystray (`tray_pystray.py`)

A regular dependency on these platforms, platform-marked in
`pyproject.toml` so macOS never installs it (pystray would drag
`pyobjc-framework-Quartz` in for a backend nuiitivet does not use there).
It is not an extra: `TrayIcon` should work out of the box, without the app
author choosing anything — the marker keeps the cost off the one platform
that has a dependency-free route, and Windows/Linux pay only Pillow and
python-xlib, marginal next to the framework's core. The conditions that
made the direct route cheap on macOS all invert here: there is no bundled bridge (cocoapy
ships inside pyglet; nothing equivalent covers Win32 shell APIs or DBus),
no existing menu machinery to reuse (`NSMenuBuilder` has no HMENU or
dbusmenu counterpart in-tree), and both platforms need a dedicated thread
anyway — a direct Win32 implementation would reproduce pystray's structure
(hidden message window, message pump, `TrackPopupMenu`, `TaskbarCreated`
re-registration) in hundreds of lines of ctypes, and a direct Linux
implementation would mean hand-rolling the StatusNotifierItem *and*
`com.canonical.dbusmenu` DBus protocols on top of a DBus library that would
itself be a new dependency. The loop-coexistence concern that ruled pystray
out on macOS does not exist on these platforms: its backends run on their
own thread by design. The bridge boundary keeps a future swap (e.g. a
direct Win32 backend) local.

pystray runs the icon on its own thread via `run_detached()`; every
activation hops to the UI thread through the runtime clock before touching
the model. Item properties are passed as
callables, but not every backend rebuilds the menu on display, so every
Observable in the menu tree also triggers `Icon.update_menu()`.

Linux is **best-effort by contract**: KDE and SNI hosts work, GNOME needs
the AppIndicator extension, bare XOrg has no menu support (install is
refused there, Decision 8), AppIndicator cannot deliver a default action
(`on_activate` degrades with a warning). The API always works; `installed`
reports the truth; the recipe degrades to a normal closing window.

## 7. Dock Visibility (macOS)

The Dock icon is per-app (`NSApplication` activation policy), so hiding all
windows leaves it behind — the asymmetry `dock_visibility` exists to manage:

- `"always"`: regular policy, untouched.
- `"auto"`: the App reports every window show/hide/open/close to
  `TrayIcon._refresh_dock`, which flips the activation policy between
  regular (≥1 visible window) and accessory (none). On `show()` the policy
  is restored *before* the window reappears and is activated.
- `"never"`: accessory from install — a pure menu-bar extra.

Windows/Linux ignore the knob; their taskbars follow window visibility
natively.
