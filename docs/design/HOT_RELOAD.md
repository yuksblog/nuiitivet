# Hot Reload

A save rebuilds the content tree from the root factory while the process, the
window, the GL context and the app's `State` values survive. The dev
bridge that drives the reloaded app is in [DEV_BRIDGE.md](DEV_BRIDGE.md); the
layout edit that lands through a reload is in [DEV_MODES.md](DEV_MODES.md).

## Overview

Four groups of modules take part: the runner that starts the app, the
controller that turns a save into a reload, the reloader that applies the
save to the user's modules, and the snapshots that carry state into the new
tree.

### Structure

```mermaid
flowchart LR
    runner[The Runner]
    controller[The Controller]
    reloader[The Reloader]
    snapshots[The Snapshots]
    tree[the widget tree]
    comments[dev/comments.py]
    edits[dev/source_edit.py]

    runner -- "the app and the root factory" --> controller
    controller -- "reload · count the old instances" --> reloader
    controller -- "snapshot · restore" --> snapshots
    controller -- "rebuild · commit" --> tree
    snapshots -- "read the old tree · write the new one" --> tree
    controller -- "restore(new root)" --> comments
    controller -- "after_reload · reload_failed" --> edits
```

| Module | Role |
| --- | --- |
| The Runner | starts the app under the dev session and keeps the root factory |
| The Controller | turns a save into one reload: the rebuild, the commit, the report |
| The Reloader | applies a save to the user's modules; counts the instances of the classes it replaced |
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
    patcher[dev/patcher.py]
    pool[remote/worker.py]
    window[runtime/window.py]
    error[dev/error_overlay.py]
    journal[dev/journal.py]
    snap[dev/snapshot.py]
    navsnap[dev/navigation_snapshot.py]
    ovsnap[dev/overlay_snapshot.py]
    comments[dev/comments.py]
    edits[dev/source_edit.py]
    slow[dev/slow_calls.py]

    watcher -- "_watched_paths() on each poll · _pending.set()" --> ctrl
    ctrl -- "paused() · reset()" --> slow
    ctrl -- "track() · reload(old_factory) · last" --> reloader
    ctrl -- "count_instances(the old classes)" --> patcher
    ctrl -- "retire_pool()" --> pool
    ctrl -- "_rebuild_content_root · _commit_content_root" --> window
    ctrl -- "snapshot_states · restore_states" --> snap
    ctrl -- "snapshot_navigation · restore_navigation" --> navsnap
    ctrl -- "snapshot_overlay · restore_overlay" --> ovsnap
    ctrl -- "restore(root)" --> comments
    ctrl -- "after_reload · reload_failed" --> edits
    ctrl -- "show_reload_error(traceback, hint) · clear_reload_error" --> error
    ctrl -- "record_success · record_error" --> journal
```

| Module | Role |
| --- | --- |
| `dev/watcher.py` | polls the user files' mtimes on a background thread; acknowledges a file the runner wrote |
| `dev/controller.py` | holds the pending event, runs the reload on the UI tick in order |
| `dev/reloader.py`, `dev/patcher.py` | apply the save to the user's modules and count the old instances (The Reloader) |
| `remote/worker.py` | the worker pool the reload retires |
| `runtime/window.py` | rebuilds the content root from the factory and commits it in place of the old one |
| `dev/error_overlay.py` | the banner over the still-running UI |
| `dev/journal.py` | records every reload, success or failure |
| `dev/snapshot.py`, `dev/navigation_snapshot.py`, `dev/overlay_snapshot.py` | the three snapshots and their restores (The Snapshots) |
| `dev/comments.py` | the comment marks matched back onto the new tree |
| `dev/source_edit.py` | the pending layout edit checked after the reload |
| `dev/slow_calls.py` | the slow-call reporter, paused for the reload, which then forgets what it reported ([DEV_BRIDGE.md](DEV_BRIDGE.md)) |

### Sequence

#### A save becomes a reload

```mermaid
sequenceDiagram
    participant F as watcher thread
    participant C as controller (UI tick)
    participant R as reloader
    participant T as patcher
    participant P as worker pool
    participant W as Window
    participant Snap as the snapshot modules
    participant Cm as Comments
    participant L as EditLog
    participant E as error overlay
    participant J as journal
    participant S as slow-call reporter

    F->>C: _pending.set()
    C->>S: paused(), until the reload ends
    C->>Snap: snapshot States, snapshot navigation
    C->>R: reload(old_factory)
    R-->>C: the modules patched, the modules re-executed with their old classes, the re-fetched factory
    C->>S: reset()
    C->>P: retire_pool()
    C->>W: _rebuild_content_root(new_factory)
    alt the reload or the rebuild raised
        C->>R: last, as far as the reload got
        C->>T: count_instances(the old classes of the edited modules)
        C->>J: record the error, with the count
        C->>E: show_reload_error(traceback, the count as a hint)
        C->>L: reload_failed(traceback)
    else built
        C->>Snap: snapshot overlay
        C->>W: _commit_content_root: unmount the old tree, clear interaction state, mount the new
        C->>Snap: restore overlay, restore States, restore navigation
        C->>Cm: restore(new root)
        alt the commit or a restore raised
            C->>R: last
            C->>T: count_instances(the old classes of the edited modules)
            C->>J: record the error, with the count
            C->>E: show_reload_error(traceback, the count as a hint)
            C->>L: reload_failed(traceback)
        else restored
            C->>E: clear the banner
            C->>L: after_reload(roots)
            C->>C: drop the snapshots
            C->>T: count_instances(the old classes of the re-executed modules)
            C->>J: record success, with the count
        end
    end
```

### Promises

- Only the content tree is rebuilt.
- A reload or a rebuild that raises leaves the previous tree on screen.
- A commit or a restore that raises is reported like a reload that raised.
  The new tree stays on screen.
- No reference into the old tree survives the commit.
- The count of old instances covers the classes a re-executed module
  defined before its re-execution. A widget is not counted.
- A successful reload's count holds no object that only the old tree or a
  snapshot kept.
- A failed reload's count covers only the re-executed modules whose own
  source changed.
- The watcher's thread changes no module and no tree.

## The Reloader

The reloader applies a save to the user's modules.

### Structure

```mermaid
flowchart LR
    ctrl[dev/controller.py]
    reloader[dev/reloader.py]
    patcher[dev/patcher.py]
    importlib[importlib]
    collector[gc]

    ctrl -- "track() · reload(old_factory) · last" --> reloader
    ctrl -- "count_instances(the old classes)" --> patcher
    reloader -- "patch_bodies(module, old source, new source) · runs_source(module, source)" --> patcher
    reloader -- "reload(module)" --> importlib
    patcher -- "unfreeze() · collect() · get_objects() · freeze()" --> collector
```

| Module | Role |
| --- | --- |
| `dev/controller.py` | asks for the reload and for the count (The Controller) |
| `dev/reloader.py` | decides which modules are the user's, keeps the source each one ran with, patches or re-executes the saved ones, re-fetches the factory |
| `dev/patcher.py` | gives living functions the code of an edited source; counts the living instances of classes |
| `importlib` | executes a module again in its namespace |
| `gc` | the collector's heap, frozen while the app runs ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |

### Sequence

#### A saved module is patched or re-executed

```mermaid
sequenceDiagram
    participant C as controller
    participant R as reloader
    participant T as patcher
    participant G as gc
    participant I as importlib

    C->>R: reload(old_factory)
    R->>R: read each user module's file
    R->>T: runs_source(module, its file), for a module with no source on record
    loop each changed module that differs only inside def bodies and imports no module to re-execute
        R->>T: patch_bodies(module, the source it ran with, the saved source)
        T->>G: unfreeze(), get_objects(), freeze()
        alt every living function fits its new code
            T-->>R: the functions took the new code
        else refused
            T-->>R: Unpatchable, no function changed
        end
    end
    loop the other changed modules, the refused ones, their importers, each after the modules it imports
        R->>I: reload(module)
    end
    R-->>C: patched, re-executed, the classes each re-executed module defined before, the factory
```

### Promises

- A user module lies under the project root, outside the install
  directories, under none of the blacklisted root packages.
- A save is compared against the source each user module last ran with.
- A module imported after startup is on record by the watcher's next poll.
- A saved module that differs from the source on record only inside def
  bodies, and imports no re-executed module, is patched. Every living
  function whose def is still in the file takes the new code.
- Any other saved module is re-executed. Every user module that imports a
  re-executed module is re-executed after it. No other module is re-executed.
- A module the patcher refuses is re-executed, with its living functions
  unchanged.
- A module whose functions do not run the source on record is never patched.
- The patcher walks the heap thawed. It refreezes a heap it found frozen.
- The factory is re-fetched by name from its module. A lambda or a local
  function is kept.

## The Snapshots

The new tree starts with fresh `State`s, a fresh navigator and a fresh
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
    snap -- "MutableStateBase.value, read and written" --> obs
    navsnap -- "snapshot_stack() · restore_stack(log)" --> navigator
    ovsnap -- "snapshot_stack() · restore_stack(records)" --> overlay
```

| Module | Role |
| --- | --- |
| `dev/snapshot.py` | walks the tree by structural path, copies every mutable `State`'s value, writes it back at the same path |
| `dev/navigation_snapshot.py` | reads the route log before the swap, replays it after the commit |
| `dev/overlay_snapshot.py` | reads the entry records before the commit, shows them again after it |
| the widget tree | what the walk reads: `children_snapshot()`, `built_child`, `key` (`widgeting/`) |
| `observable/protocols.py` | `MutableStateBase`, the value the snapshot copies |
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

- A `State`'s value is copied. The object holding it is not.
- A widget's `key` is its identity for the restore. A keyless widget is
  identified by its position and type.
- A path with no match in the new tree leaves that `State` at its initial
  value.
- Only `State`s held by a widget in the tree are restored.
- An intent is resolved by its qualified name.
- An awaited handle completes once: by its own entry, by the entry that took
  it over, or with `DISPOSED`.
- An entry shown from a widget is not recorded. It closes with the old tree.
- The record lives in the core `Overlay`.
- An entry whose intent no longer resolves does not stop the entries above
  it from being restored.
