# Tray Icon

`TrayIcon` is a model registered on the `App`, `App(window, tray=...)`. Its
menu is the `MenuEntry` model the menu bar uses ([MENU_BAR.md](MENU_BAR.md)),
with the same live sync of `label`, `enabled` and `checked`.

## Overview

Three groups of modules take part, with the menu model, the notification
backend and the clock at their edges.

### Structure

```mermaid
flowchart LR
    model[The Model]
    appwin[The App and the Window]
    bridges[The Bridges]
    menus[menus/model.py]
    nsmenu[menus/nsmenu.py]
    notify[platform/notification_win32.py]
    clock[observable/runtime.py]

    appwin -- "_install(app) · _uninstall() · _refresh_dock(visible_windows)" --> model
    model -- "install() · uninstall() · set_dock_visible(visible)" --> bridges
    bridges -- "_activate_item(entry) · _fire_activate(), on the UI thread" --> model
    model -- "MenuEntry" --> menus
    bridges -- "NSMenuBuilder" --> nsmenu
    notify -- "active_bridge().show_balloon(title, body)" --> bridges
    bridges -- "schedule_once(hop, 0)" --> clock
```

| Module | Role |
| --- | --- |
| The Model | the icon, the tooltip, the menu, `installed`, the activation of an entry |
| The App and the Window | registers the tray, installs it with the loop, reports window visibility; the window's close button and its hide and show |
| The Bridges | show the icon and the menu through AppKit, Win32 or D-Bus |
| `menus/model.py` | `MenuEntry`, the menu model shared with the menu bar ([MENU_BAR.md](MENU_BAR.md)) |
| `menus/nsmenu.py` | `NSMenuBuilder`, the `NSMenu` construction shared with the menu bar ([MENU_BAR.md](MENU_BAR.md)) |
| `platform/notification_win32.py` | the Windows notification backend |
| `observable/runtime.py` | the installed clock ([OBSERVABLE.md](OBSERVABLE.md)) |

### Promises

- The tray icon lives as long as the app's loop runs.
- `ExitPolicy` is not changed by a tray. It counts the existing windows,
  hidden ones included.
- The tray menu renders natively on every platform.
- A failed install never takes the app down.

## The Model

`TrayIcon` holds what the bridges show and runs what the bridges report.

### Structure

```mermaid
flowchart LR
    tray[TrayIcon]
    app[App]
    bridge[the platform bridge]
    entry[MenuEntry]
    clock[the installed clock]

    app -- "_install(app) · _uninstall() · _refresh_dock(visible_windows)" --> tray
    tray -- "constructs · install() · uninstall() · set_dock_visible(visible)" --> bridge
    bridge -- "schedule_once(hop, 0)" --> clock -- "_activate_item(entry) · _fire_activate()" --> tray
    tray -- "checked · role · on_select" --> entry
    tray -- "exit() for MenuRole.QUIT" --> app
```

| Module | Role |
| --- | --- |
| `TrayIcon` | holds the icon path, the tooltip, the menu and `dock_visibility`; picks the bridge per platform; publishes `installed`; runs an activated entry |
| `App` | installs and removes the tray with the loop, reports the visible-window count (The App and the Window) |
| the platform bridge | shows the icon and the menu (The Bridges) |
| `MenuEntry` | an item of the menu ([MENU_BAR.md](MENU_BAR.md)) |
| the installed clock | the hop to the UI thread ([OBSERVABLE.md](OBSERVABLE.md)) |

### Sequence

#### The tray is installed and removed

```mermaid
sequenceDiagram
    participant A as App
    participant T as TrayIcon
    participant B as the platform bridge

    A->>T: _install(app), once the loop is up
    T->>B: construct, install()
    alt install raised
        T->>T: log once, installed stays False
    else installed
        T->>T: installed = True
        T->>B: set_dock_visible(visible_window_count > 0), when dock_visibility is "auto"
    end
    A->>T: _uninstall(), when the loop stops
    T->>T: installed = False
    T->>B: uninstall()
```

#### An activation reaches the model

```mermaid
sequenceDiagram
    participant B as the platform bridge (its own thread)
    participant C as the installed clock
    participant T as TrayIcon (UI thread)
    participant E as MenuEntry

    B->>C: schedule_once(hop, 0)
    C->>T: _activate_item(entry), or _fire_activate()
    opt entry.checked is a State
        T->>E: checked = not checked
    end
    alt entry.role is QUIT
        T->>T: app.exit()
    else a window-scoped role
        T->>T: warn once, ignore
    else no role
        T->>E: on_select()
    end
```

### Promises

- `installed` is `True` only while a bridge shows the icon.
- An activation touches the model on the UI thread only.
- A tray menu does not render `shortcut`.

## The App and the Window

The app registers the tray and installs it with the loop. The window's close
button, its hide and its show are what a resident app is built from.

### Structure

```mermaid
flowchart LR
    runner[backends/pyglet/runner.py]
    app[runtime/app.py]
    window[runtime/window.py]
    tray[platform/tray.py]

    runner -- "_install_tray() · _uninstall_tray()" --> app
    app -- "_install(app) · _uninstall() · _refresh_dock(visible_windows)" --> tray
    window -- "_window_visibility_changed() on show · hide · open · close" --> app
    window -- "installed.value, before hiding the last visible window" --> tray
```

| Module | Role |
| --- | --- |
| `backends/pyglet/runner.py` | calls the install once the loop is up and the uninstall when it stops |
| `runtime/app.py` | `App` holds the registered tray, counts the visible windows, applies the exit policy to the open windows |
| `runtime/window.py` | `Window.close_action` decides what the OS close button does; `hide()` and `show()` toggle visibility; `is_visible` reports it |
| `platform/tray.py` | the registered model (The Model) |

### Sequence

#### The close button hides into the tray

```mermaid
sequenceDiagram
    participant OS as the OS close button
    participant W as Window
    participant A as App
    participant T as TrayIcon

    OS->>W: _handle_close_request()
    W->>W: read close_action
    alt "close"
        W->>W: close()
    else "hide"
        opt no other window is visible, and no tray is showing
            W->>W: warn once
        end
        W->>W: hide(): is_visible = False, set_visible(False)
        W->>A: _window_visibility_changed()
        A->>T: _refresh_dock(visible_window_count)
        opt dock_visibility is "auto"
            T->>T: bridge.set_dock_visible(visible_window_count > 0)
        end
    end
```

### Promises

- `close_action` remaps the OS close button only. `close()` and the menu
  roles always close.
- A hidden window keeps its tree, its state and its geometry. It renders no
  frames.
- A `hide()` before the backend realises the OS window creates it invisible.
- `dock_visibility="auto"` keeps the Dock icon while a window is visible and
  drops it when none is.

## The Bridges

One bridge per platform shows the icon and the menu.

### Structure

```mermaid
flowchart LR
    tray[platform/tray.py]
    cocoa[platform/tray_cocoa.py]
    win32[platform/tray_win32.py]
    sni[platform/tray_sni.py]
    nsmenu[menus/nsmenu.py]
    win32plan[platform/tray_win32_plan.py]
    sniplan[platform/tray_sni_plan.py]
    appkit["AppKit, through pyglet's cocoapy"]
    shell["Win32, through ctypes"]
    dbus["the session bus, through jeepney"]
    notify[platform/notification_win32.py]
    clock[observable/runtime.py]

    tray -- "install() · uninstall() · set_dock_visible(visible)" --> cocoa & win32 & sni
    cocoa -- "NSMenuBuilder.new_menu(entries)" --> nsmenu
    cocoa -- "statusItemWithLength_ · setActivationPolicy_" --> appkit
    win32 -- "plan_menu(entries) · load_icon_bgra(path, size)" --> win32plan
    win32 -- "RegisterClassW · CreateWindowExW · Shell_NotifyIconW · TrackPopupMenu" --> shell
    sni -- "plan_menu(entries) · load_icon_argb(path)" --> sniplan
    sni -- "RegisterStatusNotifierItem · GetLayout · LayoutUpdated · Event" --> dbus
    notify -- "show_balloon(title, body)" --> win32
    cocoa & win32 & sni -- "schedule_once(hop, 0)" --> clock
```

| Module | Role |
| --- | --- |
| `platform/tray.py` | the model the bridges show (The Model) |
| `platform/tray_cocoa.py` | an `NSStatusItem` with the menu `NSMenuBuilder` builds; switches the activation policy for the Dock |
| `platform/tray_win32.py` | a dedicated thread owning a hidden top-level window and its message loop; the icon through `Shell_NotifyIcon`; the menu built per right click; the balloon |
| `platform/tray_sni.py` | a `StatusNotifierItem` and its `dbusmenu` on the session bus; a receiver thread serving the desktop's calls; registers again when the watcher's bus name changes owner |
| `menus/nsmenu.py` | `NSMenuBuilder`, shared with the menu bar ([MENU_BAR.md](MENU_BAR.md)) |
| `platform/tray_win32_plan.py` | flattens the menu into Win32 items and command ids; decodes the icon with skia |
| `platform/tray_sni_plan.py` | flattens the menu into a dbusmenu layout and item ids; decodes the icon with skia |
| AppKit | the status bar and the application's activation policy |
| Win32 | the notification area and the popup menu |
| the session bus | the desktop's `StatusNotifierWatcher`, which draws the icon and the menu |
| `platform/notification_win32.py` | the Windows notification backend |
| `observable/runtime.py` | the installed clock ([OBSERVABLE.md](OBSERVABLE.md)) |

### Sequence

#### The desktop asks for the menu again

```mermaid
sequenceDiagram
    participant T as TrayIcon
    participant S as tray_sni.py
    participant D as the session bus

    T->>S: a label, enabled or checked changed, through its subscription
    S->>S: revision += 1
    S->>D: LayoutUpdated(revision, root)
    D->>S: GetLayout
    S->>S: plan_menu(entries), afresh
    S-->>D: the layout, ids in tree order
    D->>S: Event(id, "clicked")
    S->>T: hop: _activate_item(entry)
```

### Promises

- A bridge keeps no menu state between the desktop's requests. The model is
  the only copy.
- While a tray is installed, a Windows notification balloon hangs on its
  icon. Without one the notification backend adds a transient icon of its
  own.
- Windows and Linux decode the icon with skia. macOS hands the file to
  AppKit.
