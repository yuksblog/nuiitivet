# Tray Icon

`nv.TrayIcon` puts your app in the system tray — the right side of the menu
bar on macOS, the notification area on Windows, the status area on Linux. It
is declarative data registered on the App, exactly like the menu bar on a
Window: construct it, hand it to `App(window, tray=...)`, and it is installed
when the app starts and removed when the app exits. It lives exactly as long
as the app runs — it has no lifecycle of its own, and it never changes when
the app exits (that stays the `exit_policy`'s job).

```python
tray = nv.TrayIcon(
    icon="assets/tray.png",
    tooltip="My Sync App",
    menu=[
        nv.MenuBarItem("Open", on_select=lambda: window.show()),
        nv.MenuBarItem.separator(),
        nv.MenuBarItem.quit(),
    ],
)
app = nv.App(window, tray=tray)
```

Runnable demos:
[`samples/window/tray_icon.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/tray_icon.py)
(the basics) and
[`samples/window/close_to_tray.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/close_to_tray.py)
(a resident app).

## The menu is the same model as the menu bar

`menu=` takes the same `MenuBarItem` entries as
[the menu bar](menu_bar.md): actions, separators, nested submenus, checkable
items, and Observable `label` / `enabled` / `checked` that update the native
menu live. Two differences:

- **Include `MenuBarItem.quit()`.** For a resident app the tray menu is the
  only exit path while no window is visible; nothing is injected for you.
- **Window-scoped standard items** (`close_window()`, `minimize()`, ...) have
  no target window in a tray menu and are ignored with a warning. `quit()`
  works — it is app-scoped.

The tray menu always renders **natively** — a Win32 popup on Windows, the
desktop shell's menu on Linux, `NSMenu` on macOS — because it must work while
no window exists. `shortcut=` is not displayed there (tray menus have no
accelerator convention).

## `installed`: whether the icon is actually showing

`tray.installed` is an `Observable[bool]`: `False` until the backend installs
the icon, `True` while it shows, `False` again after removal — or forever, on
a platform that cannot host one. **A failed install never takes the app
down**; it is logged once and the app runs without a tray. If your app treats
the tray as essential, read `installed` and decide yourself — fall back to a
normal close button (the recipe below), show a hint, or exit.

## Close to tray: the resident-app recipe

A resident app — one that hides instead of closing and is summoned from the
tray — is three independent declarations. Each keeps its meaning if the
others are removed:

```python
tray = nv.TrayIcon(
    tooltip="My Sync App",
    dock_visibility="auto",
    menu=[
        nv.MenuBarItem("Open", on_select=lambda: window.show()),
        nv.MenuBarItem.separator(),
        nv.MenuBarItem.quit(),
    ],
)
window = nv.Window(
    content=build,
    close_action=tray.installed.map(lambda ok: "hide" if ok else "close"),
)
app = nv.App(window, tray=tray, exit_policy=nv.ExitPolicy.EXPLICIT)
```

- **`exit_policy=EXPLICIT`** — only `MenuBarItem.quit()` / `ExitAppIntent` /
  `app.exit()` ends the app. See
  [Multiple Windows](multi_window.md) for the exit policies; the tray never
  overrides them.
- **`close_action=...`** — what the OS close button does: `"close"` (default)
  destroys the window, `"hide"` parks it. It accepts an Observable, and the
  binding above is the important part: hide **only while the tray icon is
  actually showing**. If the tray failed to install (see the Linux section),
  the close button quietly keeps meaning close, and the user is never locked
  out of an app they cannot reach. Hard-coding `close_action="hide"` skips that
  safety; hiding the last visible window with no tray showing logs a warning.
- **`tray=...`** — the way back in, plus the way out (`quit()`).

## `hide()` and `show()`

`Window.hide()` and `Window.show()` are ordinary window operations, useful
with or without a tray:

- Hidden is **not** closed: the widget tree, its state, and the window
  geometry stay alive, and the window still counts for the exit policy.
  `show()` brings everything back instantly, focused — and on an
  already-visible window it acts as "summon": raise and refocus.
- On Windows and Linux the taskbar entry disappears with the window and
  returns with it — nothing to configure.
- A hidden window renders no frames, so a parked app costs no idle CPU for
  drawing.
- `window.is_visible` is an `Observable[bool]` if you need to react to it.
- Calling `hide()` **before** `app.run()` makes the window start hidden —
  the start-in-tray launch shape for sync clients and monitors.

## `dock_visibility` (macOS)

On macOS the Dock icon belongs to the *app*, not to a window, so hiding every
window still leaves the Dock icon by default. `TrayIcon(dock_visibility=...)`
chooses the policy:

- `"always"` (default) — the app stays in the Dock and Cmd+Tab.
- `"auto"` — in the Dock only while some window is visible; hide the last
  window and the app becomes a menu-bar-only presence until summoned. This
  is the close-to-tray convention.
- `"never"` — a pure menu-bar extra: no Dock icon, no Cmd+Tab entry, ever.

Windows and Linux ignore this — their taskbars already follow window
visibility on their own.

## `on_activate` and platform conventions

`on_activate=` runs when the icon itself is activated the way the platform
does it — but treat it as an optional shortcut and always keep an equivalent
menu entry, because support varies:

| Platform | Gesture |
| --- | --- |
| macOS | Only without a `menu` — a menu owns the click there |
| Windows | Double-click |
| Linux (AppIndicator) | Not deliverable (a pystray limitation) |

## The icon image

Pass `icon=` a path to a small PNG. On macOS, a filename stem ending in
`Template` (e.g. `trayTemplate.png`) is loaded as a template image, so the
system recolors it correctly for light and dark menu bars — the native
convention for menu-bar icons. Without `icon=`, macOS shows the tooltip text
in the menu bar and the other platforms show a neutral placeholder; ship a
real icon.

## Linux is best-effort

Nothing to install anywhere — the Windows/Linux backend
([pystray](https://pystray.readthedocs.io/)) ships with nuiitivet on those
platforms. But on Linux, whether an icon actually appears depends on the
desktop: KDE and most
SNI-capable environments work; GNOME needs the AppIndicator extension; a bare
XOrg session cannot show a menu at all (a menu-carrying tray refuses to
install there, so `installed` stays `False` and the recipe above degrades
cleanly). This is exactly what `installed` is for — the API always works, and
the app can always tell whether the icon is really there.
