# App and Window

`App` is the process. It owns the event loop, the theme source and the
registry of windows. `Window` is one OS window with its widget tree,
overlay, navigator, focus state and menu bar.

## Overview

Three modules take part, with the protocols, the dev session and the
platform integrations at their edges.

### Structure

```mermaid
flowchart LR
    app[runtime/app.py]
    window[runtime/window.py]
    runner[backends/pyglet/runner.py]
    protocols[runtime/protocols.py]
    session[dev/session.py]
    tray[platform/tray.py]
    code[the app's code]

    code -- "App(window, theme, exit_policy) · run() · App.of(context).exit()" --> app
    code -- "Window(content, title, width, chrome, menu, parent, modal, ...) · open() · close() · Window.of(context)" --> window
    window -- "_register_window(self) · _unregister_window(self) · current_app()" --> app
    app -- "close() · window.root · invalidate()" --> window
    app -- "run_app(app, draw_fps, renderer)" --> runner
    runner -- "_realize_window(app, win, event_loop) · _render_frame(dt)" --> window
    runner -- "_realize_window_hook · _event_loop · _install_tray()" --> app
    app -- "session.attach(app, root_factory, draw_fps, renderer)" --> session
    app -- "is a: AppProtocol" --> protocols
    window -- "is a: WindowProtocol" --> protocols
    app -- "_install(app) · _uninstall()" --> tray
```

| Module | Role |
| --- | --- |
| `runtime/app.py` | `App`: the open windows, the main window, the exit policy, the theme fan-out, `run`; `AppScope`, the outermost widget of every window's tree |
| `runtime/window.py` | `Window`: the lifecycle, the tree with its navigator and overlay, the input dispatch, the frame; `WindowScope`, under the `AppScope` |
| `backends/pyglet/runner.py` | the event loop and the OS window of each `Window` |
| `runtime/protocols.py` | `AppProtocol` and `WindowProtocol`, what a ViewModel is typed against |
| `dev/session.py` | takes the app over from `run()` under the dev runner ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| `platform/tray.py` | installed with the loop ([TRAY_ICON.md](TRAY_ICON.md)) |
| the app's code | constructs the app and its windows, resolves them by `.of()` |

### Promises

- Every window-flavoured keyword lives on `Window`. `App` takes none.
- Nothing below `Window` knows which window hosts it.
- `Window.of(context).close()` closes the context's own window. An operation
  addresses the object it was resolved through.

## The App

`App` holds the open windows in open order. It decides when `run()` returns.

### Structure

```mermaid
flowchart LR
    app[runtime/app.py]
    window[runtime/window.py]
    runner[backends/pyglet/runner.py]
    manager[theme/manager.py]
    dependency[theme/dependency.py]
    lookup[widgeting/context_lookup.py]
    session[dev/session.py]
    code[the app's code]

    code -- "App(window, theme, exit_policy) · run(draw_fps, renderer) · exit(code) · set_theme(theme) · render_to_png(path)" --> app
    window -- "_register_window(self) · _unregister_window(self)" --> app
    app -- "_attach_app(self) · close() · window.root · _background_uses_theme() · _update_background_color() · invalidate() · render_to_png(path)" --> window
    app -- "ThemeManager(theme) · set_theme(theme) · on_change" --> manager
    app -- "invalidate_theme_readers(window.root)" --> dependency
    app -- "find_app_scope(context)" --> lookup
    app -- "run_app(app, draw_fps, renderer) · _stop_loop()" --> runner
    app -- "attach(app, root_factory, draw_fps, renderer)" --> session
```

| Module | Role |
| --- | --- |
| `runtime/app.py` | `App`: the window list, the main window, `ExitPolicy`, the one `ThemeManager`, the loop handle, the realise hook; `AppScope` |
| `runtime/window.py` | registers on open, unregisters on close (The Window) |
| `backends/pyglet/runner.py` | the loop `run()` blocks on (The Runner) |
| `theme/manager.py` | holds the current theme ([STYLE_THEME.md](STYLE_THEME.md)) |
| `theme/dependency.py` | invalidates the theme readers of one tree ([THEME_CONSUMPTION.md](THEME_CONSUMPTION.md)) |
| `widgeting/context_lookup.py` | the walk to the `AppScope` behind `App.of` |
| `dev/session.py` | the hand-off that makes `run()` return at once ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| the app's code | holds the app, calls `exit` through `AppProtocol` |

### Sequence

#### A window closes and the exit policy fires

```mermaid
sequenceDiagram
    participant W as runtime/window.py
    participant A as runtime/app.py
    participant R as backends/pyglet/runner.py

    W->>A: _unregister_window(window)
    A->>A: remove from the open windows
    alt exiting already
        Note over A: nothing
    else MAIN_WINDOW_CLOSED, and this is the main window
        A->>A: exit()
        A->>W: close(), each open window, children before parents
        A->>R: _stop_loop()
    else no window remains, and the policy is not EXPLICIT
        A->>R: _stop_loop()
    end
```

### Promises

- `exit()` closes every window under every policy.
- A hidden window counts as open.
- A theme change is fanned out by the app to every open window. No scope
  wires a callback.

## The Window

A `Window` is a model until `open()`. `open()` turns it into a mounted
tree. `close()` finishes the object.

### Structure

```mermaid
flowchart LR
    window[runtime/window.py]
    app[runtime/app.py]
    runner[backends/pyglet/runner.py]
    navigation[navigation/navigator.py]
    overlay[overlay/overlay.py]
    chrome[runtime/chrome.py]
    geometry[layout/geometry.py]
    menubar[menubar/controller.py]
    ime[platform/ime.py]
    lookup[widgeting/context_lookup.py]
    code[the app's code]

    code -- "Window(...) · open() · close() · hide() · show() · minimize() · maximize() · ... · Window.of(context)" --> window
    window -- "current_app() · _register_window(self) · _unregister_window(self) · windows" --> app
    runner -- "_dispatch_mouse_press · _dispatch_key_press · _dispatch_text · ... · _handle_close_request()" --> window
    window -- "Navigator(content) · _stack.top()" --> navigation
    window -- "overlay_factory()" --> overlay
    window -- "CustomChrome.header · WindowDragArea" --> chrome
    window -- "Geometry(root)" --> geometry
    window -- "MenuBarController(self, menu) · install_platform_bridge() · os_focus_changed · window_closed" --> menubar
    window -- "IMEManager()" --> ime
    window -- "find_provider(context, WindowScope)" --> lookup
```

| Module | Role |
| --- | --- |
| `runtime/window.py` | `Window`: the lifecycle state, the root factory, the chrome, the modal gates in the dispatch, the close action, the frame; `WindowScope` |
| `runtime/app.py` | the registry and the current app (The App) |
| `backends/pyglet/runner.py` | delivers the OS events (The Runner) |
| `navigation/navigator.py` | the root navigator, one per window ([NAVIGATION.md](NAVIGATION.md)) |
| `overlay/overlay.py` | the overlay, one per window ([OVERLAY.md](OVERLAY.md)) |
| `runtime/chrome.py` | the OS title bar, or a header drawn in the tree |
| `layout/geometry.py` | the root `Geometry` ([GEOMETRY.md](GEOMETRY.md)) |
| `menubar/controller.py` | the menu bar, one per window ([MENU_BAR.md](MENU_BAR.md)) |
| `platform/ime.py` | the IME geometry, one per window ([TEXT_EDITING.md](TEXT_EDITING.md)) |
| `widgeting/context_lookup.py` | the ancestor search behind `Window.of` |
| the app's code | opens, closes and operates windows |

### Sequence

#### A window opens

```mermaid
sequenceDiagram
    participant C as the app's code
    participant W as runtime/window.py
    participant N as navigation/navigator.py
    participant O as overlay/overlay.py
    participant A as runtime/app.py

    C->>W: open()
    W->>W: refuse when open, closed, or the parent is not open
    W->>A: current_app(), when not attached
    W->>W: root_factory()
    W->>N: Navigator(content), unless the content is one
    W->>O: overlay_factory()
    W->>W: Stack([navigator, overlay]), the chrome, AppScope > WindowScope > Geometry
    W->>W: root.mount(self)
    W->>A: _register_window(self)
    A->>A: _realize_window_hook(window), when the loop runs
```

### Promises

- A closed window stays closed. A reload never resurrects one.
- Every open window's tree is `AppScope > WindowScope > Geometry > the
  content`. The scopes make the app and the window findable and do nothing
  else.
- Closing a parent closes its children first, transitively.
- A window blocked by an open modal child consumes keyboard input. It drops
  pointer input. The gates sit in the dispatch entry points, below every OS
  event path.

## The Runner

The pyglet runner owns the process-wide setup and the loop. It turns each
open `Window` into an OS window.

### Structure

```mermaid
flowchart LR
    runner[backends/pyglet/runner.py]
    loop[backends/pyglet/event_loop.py]
    window[runtime/window.py]
    app[runtime/app.py]
    clock[observable/runtime.py]
    pyglet[pyglet]
    callbacks[widgeting/callbacks.py]

    app -- "run_app(app, draw_fps, renderer)" --> runner
    runner -- "ResponsiveEventLoop(draw, fps, keep_running_without_windows) · run()" --> loop
    runner -- "set_ui_thread() · set_clock(clock)" --> clock
    runner -- "_realize_window_hook = _realize · _event_loop · _install_tray() · _uninstall_tray()" --> app
    runner -- "pyglet.window.Window(...) · the event handlers · the GPU context · the IME and first-mouse patches" --> pyglet
    runner -- "_render_frame(dt) · _dispatch_*(...) · _handle_close_request() · _on_window_created() · _set_os_active(active)" --> window
    runner -- "drop_pending_tasks()" --> callbacks
```

| Module | Role |
| --- | --- |
| `backends/pyglet/runner.py` | `run_app`: the DPI awareness, the clock, the loop, the realise hook, the tray; `_realize_window`: the pyglet window, its event wiring, the per-window GPU state, the patches |
| `backends/pyglet/event_loop.py` | `ResponsiveEventLoop`: draws the open windows on demand, keeps running without windows when told to ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `runtime/window.py` | the host protocol the OS events are dispatched into (The Window) |
| `runtime/app.py` | the windows to realise, the hook for later ones (The App) |
| `observable/runtime.py` | the UI thread and the clock ([OBSERVABLE.md](OBSERVABLE.md)) |
| `pyglet` | the windows, the GL context, the events |
| `widgeting/callbacks.py` | the async work left pending when the loop ends ([ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md)) |

### Sequence

#### The loop starts and ends

```mermaid
sequenceDiagram
    participant A as runtime/app.py
    participant R as backends/pyglet/runner.py
    participant K as observable/runtime.py
    participant W as runtime/window.py
    participant L as backends/pyglet/event_loop.py
    participant Cb as widgeting/callbacks.py

    A->>R: run_app(app, draw_fps, renderer)
    R->>K: set_ui_thread(), set_clock(pyglet.clock)
    R->>L: ResponsiveEventLoop(draw, fps, keep_running_without_windows)
    R->>K: set_clock(event_loop.clock)
    R->>A: _realize_window_hook = _realize
    loop each window open so far, in open order
        R->>R: _realize_window(app, win, event_loop)
        R->>W: _on_window_created()
    end
    R->>A: _install_tray()
    R->>L: run()
    Note over L: the loop ended
    R->>Cb: drop_pending_tasks()
    R->>A: _uninstall_tray(), _realize_window_hook = None
```

### Promises

- The UI thread is the thread that installs the clock.
- Every open window has an OS window while the loop runs.
- A window's OS events enter the `Window`'s dispatch methods. Nothing in the
  runner reads the tree.
