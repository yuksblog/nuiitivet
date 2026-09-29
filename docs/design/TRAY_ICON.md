# Tray Icon Design

`TrayIcon` is a model registered on `App`, `App(window, tray=...)` beside
`exit_policy=`, mirroring `Window(menu=...)`. It must exist while no window
does, so a widget-tree API could not be truthful. Its menu is the shared
`MenuEntry` model of [MENU_BAR.md](MENU_BAR.md), with the same live sync of
`label`, `enabled` and `checked`; a window-scoped standard item has no
target window in a tray menu and is ignored with a warning, `quit()` works,
and `shortcut` is not rendered, since tray menus have no accelerator
convention.

## Lifetime and Exit

The tray icon lives exactly as long as the app runs, installed when the loop
starts and removed when it stops, with no lifetime condition or teardown of
its own. `ExitPolicy` is untouched and counts existing windows, hidden ones
included; a resident app declares `ExitPolicy.EXPLICIT`, the one place app
lifetime is decided. An earlier design that suspended window-based exit
while a tray was installed was rejected: the hidden coupling made behaviour
unpredictable from the call site.

The close button's meaning is a `Window` property, `close_action="close" |
"hide"`, observable-capable. It is not `on_close`, since the `on_*` prefix
is the callback convention and this is a policy value, and there is no
`close_to_tray=True` on the tray, because a flag that silently rewires a
different object's behaviour is unreadable. Only the OS close button is
remapped, through `Window._handle_close_request()`; programmatic `close()`
and the menu roles always close.

There is no automatic fallback; a dangerous state warns. Hiding the last
visible window with no tray showing logs a one-time warning and behaves as
written. The framework makes the state knowable through
`TrayIcon.installed`, an `Observable[bool]`, and adapting is the app's job:
the resident recipe binds `close_action` to `installed.map(lambda ok: "hide"
if ok else "close")`, one visible line, the Qt and Electron division of
responsibility. An install failure never takes the app down, the
`Desktop.notify` policy, logged once; an app that treats the tray as
essential reads `installed` and fails fast itself. `installed` means the
user can reach the app through the tray: on a backend that cannot show a
menu at all, pystray's bare-XOrg backend, a menu-carrying tray refuses to
install rather than reporting an icon the user cannot operate, which would
steer the recipe toward locking the user out.

`on_activate` is an optional shortcut, not a primary affordance: macOS
delivers it only without a menu, since a menu owns the click; Windows on
double-click; a Linux AppIndicator host not at all. An equivalent menu entry
must always exist. Activation mirrors `MenuBarController.activate` minus the
window scope, always on the UI thread.

## Visibility Is Not Lifecycle

The window lifecycle stays one-way, created to open to closed
([APP_WINDOW.md](APP_WINDOW.md)); `hide()` and `show()` toggle the
visibility of an open window whose tree, state and geometry survive. A hidden
window renders no frames and still counts for the exit policy, and on Windows
and Linux the taskbar entry follows it. `show()` on an already-visible window
is a summon, raise and refocus. Hiding before the backend realises the OS
window records the state and creates the window invisible, the
start-in-tray launch shape with no flash.

The resident-app recipe is therefore three independent declarations,
`ExitPolicy.EXPLICIT`, `close_action` bound to `installed`, and the
`TrayIcon`, each meaningful without the others.

The macOS Dock icon belongs to the app, not to a window, so hiding every
window leaves it behind, the asymmetry `dock_visibility` manages:
`"always"` leaves the regular activation policy; `"auto"` has the app report
every show, hide, open and close to `TrayIcon._refresh_dock`, which flips
between regular and accessory by whether a window is visible, restoring
regular before a shown window reappears; `"never"` is accessory from
install, a pure menu-bar extra. Windows and Linux ignore the knob.

## Platform Backends

The model is backend-agnostic and `TrayIcon._create_bridge()` picks per
platform. The tray menu renders natively everywhere, because it must work
with no window on screen, unlike the menu bar's in-app fallback.

**macOS** talks to AppKit directly (`platform/tray_cocoa.py`) through
pyglet's bundled `cocoapy`, exactly like the menu bar's `NSMenu` bridge: no
dependency, no extra thread, and the pumped event loop hosts it unchanged.
`NSMenuBuilder` builds the menu, so both native surfaces share construction,
the ObjC action target and live observable sync. Menu tracking pauses
painting in Cocoa's modal tracking loop, identical to the global menu bar
and accepted. pystray was rejected here: it wants to own `NSApplication`,
and the direct route removes the one structural risk, handing part of the
main loop to an outside library.

**Windows and Linux** use pystray (`platform/tray_pystray.py`), a regular
dependency platform-marked in `pyproject.toml` so macOS never installs it
(it would drag `pyobjc-framework-Quartz` in for a backend not used there).
It is not an extra, because `TrayIcon` must work without the app author
choosing anything, and the marker keeps the cost off the one platform with a
dependency-free route. A direct implementation was rejected because every
condition that made it cheap on macOS inverts: no bundled bridge covers Win32
shell APIs or DBus, `NSMenuBuilder` has no HMENU or dbusmenu counterpart,
and both platforms need a dedicated thread anyway, so a direct Win32 backend
would reproduce pystray's structure in hundreds of lines of ctypes and a
direct Linux one would hand-roll the StatusNotifierItem and dbusmenu
protocols on a DBus library that is itself a new dependency. The bridge
boundary keeps a future swap local.

The icon runs detached, but the backend families differ. `win32` and `xorg`
spin their own thread, so their callbacks arrive off the UI thread.
`appindicator` and `gtk` start no loop: they queue every icon operation,
including the initial show that registers the item on DBus, onto the GLib
main context and assume the host runs a GLib loop. nuiitivet runs only
pyglet's, so the bridge iterates the default GLib context from a 60 Hz clock
interval on the UI thread; without that pump nothing is dispatched and the
icon never appears while `install()` returns cleanly, a silent failure that
would strand the close-to-tray recipe with a hidden window and no icon to
restore it. Every activation hops to the UI thread through the runtime clock
before touching the model, and every observable in the menu tree also
triggers `Icon.update_menu()`, since not every backend rebuilds the menu on
display.

Linux is best-effort by contract: KDE and SNI hosts work, GNOME needs the
AppIndicator extension, bare XOrg has no menu support and refuses install,
and AppIndicator cannot deliver `on_activate`. The API always works,
`installed` reports the truth, and the recipe degrades to a normal closing
window.
