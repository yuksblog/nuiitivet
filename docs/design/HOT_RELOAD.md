# Hot Reload

A save rebuilds the content tree from the root factory while the process, the
window, the GL context and the app's `Observable` values survive. The dev
bridge that drives the reloaded app is in [DEV_BRIDGE.md](DEV_BRIDGE.md); the
layout edit that lands through a reload is in [DEV_MODES.md](DEV_MODES.md).

## Overview

Three groups of modules take part: the runner that starts the app, the
controller that turns a save into a reload, and the snapshots that carry
state into the new tree.

### Structure

```mermaid
flowchart LR
    runner[The Runner]
    controller[The Controller]
    snapshots[The Snapshots]
    tree[the widget tree]
    comments[dev/comments.py]
    edits[dev/source_edit.py]

    runner -- "the app and the root factory" --> controller
    controller -- "snapshot · restore" --> snapshots
    controller -- "rebuild · commit" --> tree
    snapshots -- "read the old tree · write the new one" --> tree
    controller -- "restore(new root)" --> comments
    controller -- "after_reload · reload_failed" --> edits
```

| Module | Role |
| --- | --- |
| The Runner | starts the app under the dev session and keeps the root factory |
| The Controller | turns a save into one reload: modules, rebuild, commit, the report |
| The Snapshots | copy what the old tree held into the new one |
| the widget tree | what is rebuilt and restored |
| `dev/comments.py` | the comment marks, matched back after a rebuild ([DEV_MODES.md](DEV_MODES.md)) |
| `dev/source_edit.py` | the pending layout edit, checked after a reload ([DEV_MODES.md](DEV_MODES.md)) |

### Promises

- User code carries no dev/prod branch.
- The tree is rebuilt only by re-invoking the root factory.
- The framework's own modules are never reloaded.

## The Runner

The dev runner imports the user's module, calls `main()`, and takes the app
and its root factory from `App.run()`.

### Structure

```mermaid
flowchart LR
    main[dev/__main__.py]
    loader[dev/loader.py]
    session[dev/session.py]
    module[the user module]
    app[runtime/app.py]
    window[runtime/window.py]
    controller[dev/controller.py]

    main -- "set_dev_session(DevSession())" --> session
    main -- "load_app_module · resolve_entry" --> loader -- "import under the real name" --> module
    main -- "main()" --> module -- "App(Window(content=factory)).run()" --> app
    app -- "attach(app, root_factory)" --> session
    window -. "_root_factory · _hot_reload_inert" .-> app
    session -- "the app and the factory" --> controller
```

| Module | Role |
| --- | --- |
| `dev/__main__.py` | parses the command, sets the app's `sys.argv`, drives the loop |
| `dev/loader.py` | turns the launch target into a real module name, puts the package root on `sys.path`, finds the entry |
| `dev/session.py` | the process-global `DevSession` the app attaches to |
| the user module | the app's own code, with its `main()` |
| `runtime/app.py` | `App.run()` hands the app to the session when one is installed |
| `runtime/window.py` | holds the root factory, or marks the window inert (The Controller) |
| `dev/controller.py` | receives the app and the factory (The Controller) |

### Sequence

#### The app starts under the runner

```mermaid
sequenceDiagram
    participant R as dev runner
    participant M as user module
    participant A as App.run()
    participant S as dev session

    R->>S: install
    R->>R: sys.argv = the app's
    R->>M: import under its real name
    R->>M: main(), once
    M->>A: App(Window(content=factory)).run()
    A->>S: attach(app, factory), return without blocking
    R->>R: drive the loop, watch files, reload
```

### Promises

- `main()` runs once per process.
- The user's module is imported under its real name, never `__main__`.
- The app sees its own `sys.argv`. The runner's is never restored.
- A window whose content or overlay is a widget instance is inert to reload.

## The Controller

One save becomes one reload on the UI thread.

### Structure

```mermaid
flowchart LR
    watcher[dev/watcher.py]
    ctrl[dev/controller.py]
    reloader[dev/reloader.py]
    pool[remote/worker.py]
    window[runtime/window.py]
    error[dev/error_overlay.py]
    journal[dev/journal.py]
    snap[dev/snapshot.py]
    navsnap[dev/navigation_snapshot.py]
    ovsnap[dev/overlay_snapshot.py]
    comments[dev/comments.py]
    edits[dev/source_edit.py]

    watcher -- "_pending.set() from the poll thread" --> ctrl
    ctrl -- "reload_user_modules(project_root, old_factory)" --> reloader
    ctrl -- "retire_pool()" --> pool
    ctrl -- "_rebuild_content_root · _commit_content_root" --> window
    ctrl -- "snapshot_observables · restore_observables" --> snap
    ctrl -- "snapshot_navigation · restore_navigation" --> navsnap
    ctrl -- "snapshot_overlay · restore_overlay" --> ovsnap
    ctrl -- "restore(root)" --> comments
    ctrl -- "after_reload · reload_failed" --> edits
    ctrl -- "show_reload_error · clear_reload_error" --> error
    ctrl -- "record_success · record_error" --> journal
```

| Module | Role |
| --- | --- |
| `dev/watcher.py` | polls the user files' mtimes on a background thread; acknowledges a file the runner wrote |
| `dev/controller.py` | holds the pending event, runs the reload on the UI tick in order |
| `dev/reloader.py` | decides which modules are the user's, orders them, reloads them, re-fetches the factory |
| `remote/worker.py` | the worker pool the reload retires |
| `runtime/window.py` | rebuilds the content root from the factory and commits it in place of the old one |
| `dev/error_overlay.py` | the banner over the still-running UI |
| `dev/journal.py` | records every reload, success or failure |
| `dev/snapshot.py`, `dev/navigation_snapshot.py`, `dev/overlay_snapshot.py` | the three snapshots and their restores (The Snapshots) |
| `dev/comments.py` | the comment marks matched back onto the new tree |
| `dev/source_edit.py` | the pending layout edit checked after the reload |

### Sequence

#### A save becomes a reload

```mermaid
sequenceDiagram
    participant F as watcher thread
    participant C as controller (UI tick)
    participant R as reloader
    participant P as worker pool
    participant W as Window
    participant Snap as the snapshot modules
    participant Cm as Comments
    participant L as EditLog
    participant E as error overlay
    participant J as journal

    F->>C: _pending.set()
    C->>Snap: snapshot observables, snapshot navigation
    C->>R: reload_user_modules(project_root, old_factory)
    R-->>C: the reloaded modules, the re-fetched factory
    C->>P: retire_pool()
    C->>W: _rebuild_content_root(new_factory)
    alt the reload or the rebuild raised
        C->>J: record the error
        C->>E: show the banner, traceback to stderr
        C->>L: reload_failed(traceback)
    else built
        C->>Snap: snapshot overlay
        C->>W: _commit_content_root: unmount the old tree, clear interaction state, mount the new
        C->>Snap: restore overlay, restore observables, restore navigation
        C->>Cm: restore(new root)
        C->>E: clear the banner
        C->>L: after_reload(roots)
        C->>J: record success
    end
```

### Promises

- A user module lies under the project root, outside the install
  directories, under none of the blacklisted root packages.
- Every user module is reloaded on every save.
- The factory is re-fetched by name from its reloaded module.
- Only the content tree is rebuilt.
- A reload or a rebuild that raises leaves the previous tree on screen.
- No reference into the old tree survives the commit.
- The watcher only signals.

## The Snapshots

The new tree starts with fresh observables, a fresh navigator and a fresh
overlay. Each snapshot writes into the new tree what the old one held,
matched by an identity that survives the rebuild. The replay of the route
stack is in [NAVIGATION.md](NAVIGATION.md).

### Structure

```mermaid
flowchart LR
    snap[dev/snapshot.py]
    navsnap[dev/navigation_snapshot.py]
    ovsnap[dev/overlay_snapshot.py]
    tree[the widget tree]
    obs[observable/protocols.py]
    navigator[navigation/navigator.py]
    overlay[overlay/overlay.py]

    snap -- "children_snapshot() · built_child · key" --> tree
    snap -- "MutableObservableBase.value, read and written" --> obs
    navsnap -- "snapshot_stack() · restore_stack(log)" --> navigator
    ovsnap -- "snapshot_stack() · restore_stack(records)" --> overlay
```

| Module | Role |
| --- | --- |
| `dev/snapshot.py` | walks the tree by structural path, copies every mutable observable's value, writes it back at the same path |
| `dev/navigation_snapshot.py` | reads the route log before the swap, replays it after the commit |
| `dev/overlay_snapshot.py` | reads the entry records before the commit, shows them again after it |
| the widget tree | what the walk reads: `children_snapshot()`, `built_child`, `key` (`widgeting/`) |
| `observable/protocols.py` | `MutableObservableBase`, the value the snapshot copies |
| `navigation/navigator.py` | keeps the route log and replays it ([NAVIGATION.md](NAVIGATION.md)) |
| `overlay/overlay.py` | keeps the entry records, replays them, hands the old handle to the new entry ([OVERLAY.md](OVERLAY.md)) |

### Sequence

#### An awaited entry survives a reload

```mermaid
sequenceDiagram
    participant C as controller
    participant OS as dev/overlay_snapshot.py
    participant Old as the overlay before the reload
    participant New as the overlay after the reload
    participant H as the handle the app awaits

    C->>OS: snapshot_overlay()
    OS->>Old: snapshot_stack()
    Note over Old: the returned entries are carried
    C->>OS: restore_overlay(records)
    OS->>New: restore_stack(records), bottom to top
    loop each record
        alt the intent still resolves
            New->>New: replay(overlay, intent) → a new entry
            New->>H: the new entry takes over the future
        else the intent no longer resolves
            New->>H: DISPOSED
        end
    end
```

### Promises

- An observable's value is copied. The object holding it is not.
- A widget's `key` is its identity for the restore. A keyless widget is
  identified by its position and type.
- A path with no match in the new tree leaves that observable at its initial
  value.
- Only observables held by a widget in the tree are restored.
- An intent is resolved by its qualified name.
- An awaited handle completes once: by its own entry, by the entry that took
  it over, or with `DISPOSED`.
- An entry shown from a widget is not recorded. It closes with the old tree.
- The record lives in the core `Overlay`.
- An entry whose intent no longer resolves does not stop the entries above
  it from being restored.
