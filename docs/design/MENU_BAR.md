# Menu Bar

The menu is a model registered on the window, `Window(menu=...)`. One model
feeds the in-app bar on Windows and Linux and the global bar on macOS.

## Overview

Four groups of modules take part, with the window, the app and the tray at
their edges.

### Structure

```mermaid
flowchart LR
    model[The Model]
    controller[The Controller]
    bar[The In-App Bar]
    bridge[The macOS Bridge]
    window[runtime/window.py]
    app[runtime/app.py]
    tray[platform/tray.py]

    window -- "MenuBarController(window, menu) · set_model(model) · install_platform_bridge() · os_focus_changed(active) · window_closed()" --> controller
    bar -- "register_slot(slot) · activate(item)" --> controller
    controller -- "menubar_changed(active, model)" --> bar
    controller -- "MenuBarFocusCoordinator.attach(app) · window_created · focus_changed · model_changed · window_closed" --> bridge
    bridge -- "activate(entry)" --> controller
    controller -- "window.close() · minimize() · maximize() · restore() · full_screen()" --> window
    controller -- "app.exit()" --> app
    bar -- "MenuEntry · MenuBar.style · MenuBarThemeData" --> model
    bridge -- "MenuEntry · MenuBar" --> model
    tray -- "MenuEntry" --> model
```

| Module | Role |
| --- | --- |
| The Model | the entries, the bar root, the style and the palette, as data |
| The Controller | per window: the registered model, the slot that renders it, the one activation path |
| The In-App Bar | the slots and the bar widget drawn on Windows and Linux |
| The macOS Bridge | the global bar, following the focused window |
| `runtime/window.py` | holds the controller, exposes `menu`, reports the OS focus and the close ([APP_WINDOW.md](APP_WINDOW.md)) |
| `runtime/app.py` | holds the one focus coordinator, `exit()` ([APP_WINDOW.md](APP_WINDOW.md)) |
| `platform/tray.py` | the tray menu, built from the same entries ([TRAY_ICON.md](TRAY_ICON.md)) |

### Promises

- Every surface activates an entry through the controller.
- Structure is replaced wholesale through `window.menu`. `label`, `enabled`
  and `checked` move live on every surface.
- On each platform exactly one mechanism fires a menu shortcut: the in-app
  bar's bindings, or the native key equivalents.

## The Model

The entries, the bar root, the style and the palette are plain data,
rendered by whichever surface the platform has.

### Structure

```mermaid
flowchart LR
    entry[menus/model.py]
    menubar[menubar/model.py]
    mbstyle[menubar/style.py]
    themedata[menubar/theme_data.py]
    shortcut[input/shortcut.py]
    material[material/theme/material_theme.py]
    plain[theme/plain_theme.py]
    tray[platform/tray.py]
    bar[menubar/bar.py]

    menubar -- "items, a tuple of MenuEntry" --> entry
    menubar -- "style" --> mbstyle
    mbstyle -- "merged_palette(theme_data)" --> themedata
    entry -- "to_shortcut(spec) · shortcut.display" --> shortcut
    material & plain -- "register MenuBarThemeData(ColorSpec tokens)" --> themedata
    tray -- "MenuEntry" --> entry
    bar -- "theme.extension(MenuBarThemeData)" --> themedata
```

| Module | Role |
| --- | --- |
| `menus/model.py` | `MenuEntry`, one entry: an action, a submenu, a separator or a standard item with a `MenuRole`; `label`, `enabled` and `checked` plain or `Observable` |
| `menubar/model.py` | `MenuBar`, the root holding the top-level entries and a style |
| `menubar/style.py` | `MenuBarStyle`, per-instance geometry and nullable colour overrides |
| `menubar/theme_data.py` | `MenuBarThemeData`, the palette of the bar and of its popups, neutral literals by default |
| `input/shortcut.py` | the gesture and its display form ([KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md)) |
| `material/theme/material_theme.py` | registers the Material palette, MD3 role tokens ([STYLE_THEME.md](STYLE_THEME.md)) |
| `theme/plain_theme.py` | registers the plain palette ([STYLE_THEME.md](STYLE_THEME.md)) |
| `platform/tray.py` | consumes the entries ([TRAY_ICON.md](TRAY_ICON.md)) |
| `menubar/bar.py` | reads the palette (The In-App Bar) |

### Promises

- `menus/` imports no surface. `menubar/` imports `menus/`.
- The palette holds `ColorSpec` tokens, resolved at paint.
- `MenuBarThemeData` and `MenuBarStyle` live outside `material/`. The bar
  reads its palette from `Theme.extension(MenuBarThemeData)`, never from a
  Material colour role.

## The Controller

One controller per window holds the model. Every activation runs through
it. It chooses the slot that renders.

### Structure

```mermaid
flowchart LR
    controller[menubar/controller.py]
    window[runtime/window.py]
    app[runtime/app.py]
    slots[menubar/slots.py]
    bar[menubar/bar.py]
    focus[menubar/focus.py]
    nsmenu[menubar/nsmenu.py]
    builder[menus/nsmenu.py]
    entry[menus/model.py]

    window -- "MenuBarController(window, menu) · set_model(model) · install_platform_bridge() · os_focus_changed(active) · window_closed()" --> controller
    slots -- "register_slot(slot) · unregister_slot(slot)" --> controller
    controller -- "menubar_changed(active, model)" --> slots
    bar -- "activate(item)" --> controller
    builder -- "activate(entry)" --> controller
    controller -- "MenuBarFocusCoordinator.attach(window.app) · window_created · focus_changed · model_changed · window_closed" --> focus
    controller -- "NSMenuBridge.is_supported()" --> nsmenu
    controller -- "checked.value = not checked.value · on_select()" --> entry
    controller -- "close() · minimize() · maximize() · restore() · full_screen()" --> window
    controller -- "app.exit(), for QUIT" --> app
```

| Module | Role |
| --- | --- |
| `menubar/controller.py` | `MenuBarController`: the registered model, the registry of mounted slots, the activation of an entry, the role dispatch |
| `runtime/window.py` | creates the controller with the window, forwards `menu`, the backend window's creation, the OS focus and the close |
| `runtime/app.py` | `exit()` |
| `menubar/slots.py` | the slots that register on mount (The In-App Bar) |
| `menubar/bar.py` | activates from a popup or a shortcut (The In-App Bar) |
| `menubar/focus.py` | the coordinator the controller attaches to on macOS (The macOS Bridge) |
| `menubar/nsmenu.py` | answers whether the bridge is supported here (The macOS Bridge) |
| `menus/nsmenu.py` | activates from an `NSMenuItem`, through the `activate` the bridge handed it (The macOS Bridge) |
| `menus/model.py` | the entry activated (The Model) |

### Sequence

#### An entry is activated

```mermaid
sequenceDiagram
    participant S as bar.py, or menus/nsmenu.py
    participant C as controller.py
    participant E as menus/model.py
    participant W as runtime/window.py
    participant A as runtime/app.py

    S->>C: activate(item)
    opt item.checked is an Observable
        C->>E: checked.value = not checked.value
    end
    alt item.role is QUIT
        C->>A: exit()
    else another standard role
        C->>W: the role's method
    else item.on_select is set
        C->>E: on_select(), exceptions contained
    end
```

#### The slot that renders is chosen

```mermaid
sequenceDiagram
    participant S as slots.py
    participant C as controller.py

    S->>C: register_slot(slot), on mount
    alt a platform bridge is attached
        Note over C: no slot is active
    else a user area is mounted
        Note over C: the first mounted area is active, the rest are inert, warned once
    else
        Note over C: the most recently mounted default slot is active
    end
    C->>S: menubar_changed(active, model), every registered slot
```

### Promises

- A window-scoped role calls the owning window. `QUIT` calls that window's
  app.
- A disabled entry is never activated by a shortcut.
- The model stays on the window wherever it renders.
- A mounted user area takes over from the default slot.

## The In-App Bar

On Windows and Linux a slot builds the bar widget. A top-level entry opens a
popup through the overlay.

### Structure

```mermaid
flowchart LR
    slots[menubar/slots.py]
    bar[menubar/bar.py]
    controller[menubar/controller.py]
    window[runtime/window.py]
    menu[material/menu.py]
    overlay[overlay/overlay.py]
    keysc[modifiers/key_shortcut.py]
    theme[theme/theme.py]
    entry[menus/model.py]

    window -- "DefaultMenuBarSlot(), under the chrome when a menu is registered" --> slots
    slots -- "register_slot(self) · unregister_slot(self)" --> controller
    controller -- "menubar_changed(active, model)" --> slots
    slots -- "MenuBarWidget(model), at build when active" --> bar
    bar -- "Theme.of(self).extension(MenuBarThemeData)" --> theme
    bar -- "KeyShortcutModifier(binding).apply(bar), MOUNT" --> keysc
    bar -- "resolved_label() · resolved_enabled() · shortcut.display · label, enabled, checked subscriptions while open" --> entry
    bar -- "Menu(entries, on_dismiss, style) · MenuItem · SubMenuItem · MenuDivider · focus_first_item()" --> menu
    bar -- "Overlay.of(self, root=True).show(popup, passthrough=False, dismiss_on_outside_tap=True, position) · handle.close() · handle.done()" --> overlay
    menu -- "on_dismiss · on_click · popup_gone(popup) on unmount" --> bar
    bar -- "activate(item)" --> controller
```

| Module | Role |
| --- | --- |
| `menubar/slots.py` | `DefaultMenuBarSlot` and `MenuBarArea`: a widget marking where the bar renders; a zero-size spacer when inactive |
| `menubar/bar.py` | `MenuBarWidget`: the row of titles, the open popup, the subscriptions of the open entries, the model's shortcut bindings |
| `menubar/controller.py` | the active slot and the activation (The Controller) |
| `runtime/window.py` | inserts the default slot into the wrapped root ([APP_WINDOW.md](APP_WINDOW.md)) |
| `material/menu.py` | the popup surface, its keyboard traversal and its submenus ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |
| `overlay/overlay.py` | anchors the popup under its title ([OVERLAY.md](OVERLAY.md)) |
| `modifiers/key_shortcut.py` | the binding of each entry's shortcut ([KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md)) |
| `theme/theme.py` | the theme extension the palette comes from ([THEME_CONSUMPTION.md](THEME_CONSUMPTION.md)) |
| `menus/model.py` | the entries drawn (The Model) |

### Sequence

#### A top-level menu opens and closes

```mermaid
sequenceDiagram
    participant B as bar.py
    participant E as menus/model.py
    participant O as overlay.py
    participant M as material/menu.py

    B->>B: close_menu(), the open popup if any
    B->>M: Menu(entries, on_dismiss=close_menu, style), from the entry's submenu
    B->>O: show(popup, passthrough=False, dismiss_on_outside_tap=True, anchored under the title)
    B->>E: subscribe to label, enabled and checked of the open entries
    alt an item is clicked
        M->>B: activate(item)
        B->>B: close_menu(): handle.close(), dispose the subscriptions
    else an outside tap
        O->>M: unmount
        M->>B: popup_gone(popup)
        B->>O: handle.done()
        O-->>B: True
        B->>B: close_menu()
    else the overlay host remounts
        O->>M: unmount
        M->>B: popup_gone(popup)
        B->>O: handle.done()
        O-->>B: False, the popup stays open
    end
```

### Promises

- The popups are the MD3 `Menu` widgets. Their `MenuStyle` is derived from
  the bar's palette, never from the Material defaults.
- A popup's unmount is a dismissal only when its overlay entry is settled.
- `menubar/bar.py` imports `nuiitivet.material`. The slot imports it at its
  first build. No other module under `menubar/` imports `material`.

## The macOS Bridge

On macOS the model is installed as the application's main menu.

### Structure

```mermaid
flowchart LR
    focus[menubar/focus.py]
    nsmenu[menubar/nsmenu.py]
    builder[menus/nsmenu.py]
    controller[menubar/controller.py]
    app[runtime/app.py]
    clock[observable/runtime.py]
    appkit["AppKit, through pyglet's cocoapy"]
    entry[menus/model.py]

    controller -- "attach(app) · window_created(window) · focus_changed(window, active) · model_changed(window) · window_closed(window)" --> focus
    focus -- "windows · _main_window · title" --> app
    focus -- "NSMenuBridge(controller, app_name) · install(model) · uninstall()" --> nsmenu
    focus -- "schedule_once(apply, 0)" --> clock
    nsmenu -- "NSMenuBuilder(controller.activate) · new_menu(title, entries) · dispose()" --> builder
    nsmenu -- "setMainMenu_(main_menu)" --> appkit
    builder -- "NSMenuItem · setTitle_ · setEnabled_ · setState_ · key equivalents" --> appkit
    builder -- "label, enabled, checked subscriptions · key_equivalent(shortcut)" --> entry
    builder -- "schedule_once(apply, 0)" --> clock
    appkit -- "nuiitivetMenuAction_(sender)" --> builder
    builder -- "activate(entry)" --> controller
```

| Module | Role |
| --- | --- |
| `menubar/focus.py` | `MenuBarFocusCoordinator`: picks the window whose model belongs on the bar, owns the bridge, coalesces reinstalls onto the next tick |
| `menubar/nsmenu.py` | `plan_menus`, the arrangement with the application menu first; `NSMenuBridge`, installs the planned menus as the main menu |
| `menus/nsmenu.py` | `NSMenuBuilder`: entries to `NSMenu` trees, the action target, the retained objects, the property subscriptions; `key_equivalent` ([TRAY_ICON.md](TRAY_ICON.md) shares it) |
| `menubar/controller.py` | attaches the window, receives the activations (The Controller) |
| `runtime/app.py` | the open windows, the main window, the coordinator slot ([APP_WINDOW.md](APP_WINDOW.md)) |
| `observable/runtime.py` | the installed clock ([OBSERVABLE.md](OBSERVABLE.md)) |
| AppKit | the main menu and its items |
| `menus/model.py` | the entries installed (The Model) |

### Sequence

#### The bar follows the windows

```mermaid
sequenceDiagram
    participant W as controller.py
    participant F as focus.py
    participant K as observable/runtime.py
    participant N as nsmenu.py

    W->>F: window_created(window), the backend window is up
    F->>F: apply, at once
    W->>F: focus_changed(window, active=True), model_changed, or window_closed
    F->>K: schedule_once(apply, 0), once per burst
    K->>F: apply
    F->>F: the owner: the focused window with a menu, else the main window with one
    alt the owner and the model are the installed ones
        Note over F: nothing
    else another owner
        F->>N: NSMenuBridge(owner's controller, app_name).install(model)
        F->>N: old.uninstall()
    else the same owner, a replaced model
        F->>N: install(model), the same bridge
    end
```

#### A property changes

```mermaid
sequenceDiagram
    participant E as menus/model.py
    participant B as menus/nsmenu.py
    participant K as observable/runtime.py
    participant A as AppKit

    E->>B: a label, enabled or checked Observable fires, any thread
    B->>K: schedule_once(apply, 0)
    K->>B: apply, on the UI thread
    B->>A: setTitle_ · setEnabled_ · setState_
```

### Promises

- One coordinator and one bridge per app.
- The bar shows the focused window's model. The main window's model stands
  in for a window with `menu=None`.
- The Cocoa imports happen lazily, on macOS only. `plan_menus` and
  `key_equivalent` import on every platform.
- AppKit is touched on the UI thread only.
