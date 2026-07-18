# Hot Reload

> Status: Implemented
> Related: [#359](https://github.com/yuksblog/nuiitivet/issues/359)
> User guide: [docs/guide/advanced/hot_reload.md](../guide/advanced/hot_reload.md)

## 1. Goal

Provide Flutter-style hot reload: when a developer edits UI code and saves, the
widget tree is rebuilt in place and the change appears immediately, while the
window, the GL context, the debugger session, and the app's `Observable` state
all survive.

The design is optimised for the **VSCode F5** experience: the app launches under
the standard `debugpy` adapter, breakpoints fire as usual, and a save reloads the
tree. No custom debug adapter and no editor extension are required — reloading
modules and rebuilding a tree is ordinary Python, so `debugpy` needs nothing
special, and breakpoints (keyed by file and line) keep firing in reloaded code.

## 2. Design principles

1. **Single codebase.** The user does not maintain separate production and dev
   entry points. The same `main()` serves both paths.
2. **Import is not execution.** Importing the user's module must not start the
   event loop or run `main()`. The runner controls when execution happens.
3. **Reload via factory.** The tree is rebuilt by re-invoking a retained **root
   factory**, not by re-executing the whole user module.
4. **Side effects once.** Non-App side effects (global init, logging setup, DI
   wiring, window creation) run once at startup and never again on reload.

## 3. User contract

### 3.1 Project layout

```
yourapp/
  __main__.py   # thin entry guard: just calls main()
  app.py        # main() and the root factory live here
```

`app.py`:

```python
import nuiitivet.material as nv

def build_root() -> nv.Widget:
    # Build the root widget here. Close over any constructor arguments.
    return MyRootWidget()

def main() -> None:
    # Non-App side effects (init, DI, logging) may go here; they run once at
    # startup and never again on reload (§3.3).
    nv.App(content=build_root).run()
```

`__main__.py`:

```python
from .app import main

if __name__ == "__main__":
    main()
```

### 3.2 Pass a factory, not an instance

`App(content=...)` takes a **root factory** — a zero-argument callable returning
the root widget:

```python
nv.App(content=build_root)                                  # function (preferred)
nv.App(content=MyRootWidget)                                # a Widget subclass is a factory
nv.App(content=lambda: MyRootWidget(config, theme=dark))    # args via a closure
```

Passing a `Widget` instance still works for backward compatibility, but the tree
cannot be rebuilt from an instance, so hot reload is inert for that root; under
the dev runner this emits a one-time warning.

> Do not pass `App(content=build_root())` — the parentheses call the factory and
> hand over an instance.

A factory that needs arguments should use `lambda:`.

### 3.3 Side effects run once

Any non-App side effect inside `main()` runs **once at startup** and is **not**
re-run on reload, because the runner never re-invokes `main()` — it only calls
the retained factory again. Initialization that must run per tree build belongs
in the factory, not in `main()`.

### 3.4 Launching

Production / normal run (unchanged; `App.run()` blocks on the event loop):

```
python -m yourapp
```

Development / hot reload:

```
python -m nuiitivet.dev yourapp/app.py        # file path
python -m nuiitivet.dev --module yourapp.app  # or a dotted module name
```

VSCode `launch.json`:

```json
{
  "name": "nuiitivet: hot reload",
  "type": "debugpy",
  "request": "launch",
  "module": "nuiitivet.dev",
  "args": ["${workspaceFolder}/yourapp/app.py"],
  "console": "integratedTerminal"
}
```

## 4. Runtime flow

The production and dev paths differ only inside `App.run()`; user code carries no
dev/prod branch.

**Normal run:**

```
python -m yourapp
  → __main__.py: main()
      → App(content=build_root)   # App retains the factory
      → App.run()                 # no dev session → run_app() blocks
```

**Hot reload run:**

```
python -m nuiitivet.dev yourapp/app.py
  → runner installs a dev session (process-global)
  → runner imports the user module under its real name (main() does NOT run)
  → runner calls main() exactly once
      → App(content=build_root)   # App retains the factory
      → App.run()                 # dev session present → hands the App + factory
                                  #   to the session and returns without blocking
  → runner drives the real event loop, file watching, and reloads
```

## 5. App API

`content` accepts a `Widget` or a factory:

```python
RootFactory = Callable[[], Widget]

def __init__(self, content: "Widget | RootFactory", ...):
    if callable(content) and not isinstance(content, Widget):
        self._root_factory = content
    elif isinstance(content, Widget):
        instance = content
        self._root_factory = lambda: instance   # backward-compat; reload inert
    else:
        raise TypeError(...)
```

`App.run()` consults the dev session and hands off instead of blocking when one
is active:

```python
def run(self, draw_fps=None, *, renderer="auto"):
    session = current_dev_session()       # None outside the dev runner
    if session is not None:
        session.attach(app=self, root_factory=self._root_factory,
                       draw_fps=draw_fps, renderer=parse_renderer_mode(renderer))
        return
    run_app(self, draw_fps=draw_fps, renderer=parse_renderer_mode(renderer))
```

The dev session is a process-global handoff object (`nuiitivet.dev.session`); it
is `None` in production, which is what keeps `App.run()` blocking normally.

## 6. Content-subtree rebuild

Only the user's content tree is rebuilt on reload; the App shell — window,
chrome, theme — is preserved. `App` exposes two primitives:

- **`_rebuild_content_root(new_factory=None)`** re-invokes the factory, rebuilds
  the Navigator/Overlay stack (which resets the process-global `Navigator` and
  `Overlay` roots to the new instances), and re-wraps it with the preserved
  chrome shell and `AppScope`. It returns the new root without mounting it, so
  the reload orchestrator can snapshot old state and restore it before mount.
- **`_commit_content_root(new_root)`** unmounts the old tree, clears App-held
  interaction state that pointed into it (focus / hover / pressed targets and
  pointer captures — otherwise the old tree leaks and stale focus bleeds into the
  new tree), installs and mounts the new root, and forces a repaint.

## 7. Reload sequence

On a save detected by the file watcher, the runner (on the UI thread):

1. **Snapshot** every mutable `Observable` value in the live tree, keyed by a
   structural path (§7.4).
2. **Reload** the user's modules in dependency order (§7.1–7.2) and re-fetch the
   factory (§7.3).
3. **Rebuild** the content root (`_rebuild_content_root`), which also resets the
   global Navigator/Overlay roots.
4. **Restore** snapshot values into the matching observables of the new tree.
5. **Commit** the new root (`_commit_content_root`) and repaint.

`main()` is never called in this sequence. Every widget and `Observable` is
recreated by the factory; "preserving state" means copying `Observable` *values*
across, not carrying live objects.

On any error during steps 2–3 the previous tree is kept and the error is surfaced
(§9); the app and debug session stay alive.

### 7.1 Identifying user modules

A module is treated as the user's — and therefore reloadable — when its
`__file__` lives under the launched project root and it is outside the standard
library / `site-packages`. A name blacklist (`nuiitivet`, `skia`, `pyglet`) is
applied in addition, so the framework and the C-extension modules are never
reloaded even if a file happens to sit under the project root. This double net
satisfies the requirement that `nuiitivet`, `skia`, and `pyglet` are never
reloaded.

The file watcher's watch set is built dynamically from these modules' `__file__`
values, so newly imported user modules become watched automatically.

### 7.2 Dependency-ordered reload

All user modules are reloaded on every change, in **dependency order** (a
depended-upon leaf such as `widgets` before its dependent `app`). Reloading only
the saved file would leave a dependent's `from .widgets import W` bound to the
stale class — the classic `importlib.reload` ordering hazard. The dependency
graph is approximated from each module's globals (imported submodules and the
`__module__` of imported classes/functions) and reloaded leaves-first via a DFS
post-order; import cycles are broken arbitrarily.

Before reloading, each user module's cached `.pyc` is removed and
`importlib.invalidate_caches()` is called. `importlib.reload` only recompiles
from source when it judges the `.pyc` stale, and that check uses
second-granularity mtimes — a save in the same wall-clock second as the last
compile can be missed, reloading stale bytecode. Dropping the `.pyc` forces a
fresh compile from the edited source.

### 7.3 Re-fetching the factory

The factory captured at startup resolves its module globals at call time, so
changes *inside* the widgets it builds are picked up automatically. Changes to
the **factory definition itself** (a different root, changed arguments) are
picked up by re-fetching the factory by name from its reloaded module. This
requires the factory to be a module-level named symbol; an anonymous
(`lambda`) or locally-defined factory cannot be re-fetched, so its own definition
changes are not observed (its internal widget changes still are).

### 7.4 State snapshot & restore

Snapshot walks the mounted tree — both `children` and `built_child` (where
`ComposableWidget` state lives) — and records the value of every mutable
`Observable` held as a widget attribute, keyed by a structural path. Each path
segment is a widget's stable `key` when it has one, and otherwise its child
index + widget type; the trailing segment is the attribute name. Restore walks
the rebuilt tree the same way and writes each snapshot value back into the
observable at the matching path.

When the tree structure is unchanged (the common "tweak a padding" case) every
path matches and state is fully restored. A widget given a `key` — the same
reconciliation identity the dev action bridge targets (#375), set via
`ComposableWidget(key=...)` or the `keyed("…")` modifier — keeps its path across
a reorder or a sibling insertion, so its state survives those structural edits
too. When keyless widgets are added, removed, or reordered, unmatched paths keep
the new tree's initial value — a deliberate, documented degradation. Only in-tree
observables are handled; module-level observables are re-initialised by
`importlib.reload` and are out of scope.

## 8. Module loading and launch-target resolution

The dev runner accepts either a file path (matching the documented `launch.json`)
or a dotted module name (`--module`). Either way the module is imported under a
**real, stable name** — never `__main__` — so that `importlib.reload` can re-run
it and relative imports resolve.

For a file path, the dotted module name is recovered by walking up the directory
tree while `__init__.py` files are present (so `pkg/sub/app.py` in a package
becomes `pkg.sub.app`, and a bare script becomes its file stem); the package
root's parent is placed on `sys.path` so the import succeeds.

## 9. Threading

Widget-tree mutation is main-thread-only (`docs/design/THREADING_MODEL.md`). The
file watcher runs on a background thread and only *signals* that a file changed;
it never touches the tree. A `pyglet.clock` callback on the UI thread drains the
signal and performs the reload. A useful consequence: a save made while stopped
at a breakpoint (event loop paused) is queued and applied on resume.

## 10. Error handling

Editing is a half-broken-code activity, so a syntax or build error on save must
not tear down the app or the debug session. When a reload fails the previous tree
is kept (the orchestrator never commits the broken one) and the error is reported
two ways: the full traceback on `stderr` (visible in the VSCode debug console /
terminal) and a best-effort banner over the still-running UI, cleared on the next
successful reload.

## 11. Limitations & future work

- **Structural edits reset the affected state of keyless widgets.** State restore
  is by structural path (§7.4). A widget given a stable `key` — via
  `ComposableWidget(key=...)` or the `keyed("…")` modifier — anchors its state
  across structural changes (reorder, sibling insertion), landed in
  [#375](https://github.com/yuksblog/nuiitivet/issues/375). Keyless widgets still
  lose state when their position changes — add a `key` to opt into durable state.
- **Navigation stack and open overlays reset.** A reload rebuilds a fresh
  `Navigator` at its initial route and a fresh `Overlay`, so pushed routes and
  open dialogs are dropped. Overlays are transient and bound to an in-flight
  awaited coroutine, so resetting them is the intended, safe default. Restoring
  the navigation stack is feasible for declarative (intent / route-table)
  navigation and is tracked in
  [#378](https://github.com/yuksblog/nuiitivet/issues/378); imperative
  instance-based `push(Screen())` is fundamentally unrestorable (same
  instance-vs-factory constraint as the root).
- **Module-level state is not restored** (§7.4).

## 12. Dev bridge & MCP server

Hot reload lets an author *edit* a live app; the **dev bridge** lets a tool *see*
and *drive* it, closing a perception–action loop over reload: edit (reload) →
`describe_tree` / `screenshot` (see) → `click` / `type` / `key` (act) → verify →
edit again.

- **Bridge** (`dev/bridge.py`, [#374](https://github.com/yuksblog/nuiitivet/issues/374)).
  A localhost-only `ThreadingHTTPServer` on an ephemeral port, started by the dev
  runner alongside hot reload. It refuses to start without an active dev session,
  so it is never opened in production. Each request that touches the widget tree
  is marshalled onto the UI thread (same watcher-thread → clock-drain primitive
  hot reload uses; see §9). The bound port is published to
  `<project_root>/.nuiitivet/dev-bridge.json` for clients to discover.
- **Perception** (`dev/perception.py`, #374). `describe_tree` walks the mounted
  tree into compact JSON — per node its type, human identity (`key` / `label` /
  `text` / `title`) and `rect` `[x, y, w, h]` in root coordinates. This is the
  semantic, low-token view a tool reasons over and resolves action targets from.
  `screenshot` renders the current frame to PNG.
- **Action** (`dev/action.py`, [#375](https://github.com/yuksblog/nuiitivet/issues/375)).
  `click` / `type` / `key` synthesize the same input the real backend delivers.
  Targeting is by *stable identifier* (`key` / `label`), resolved to a rect
  centre, so it survives layout changes; raw coordinates are a fallback. Every
  verb `settle`s (flush reactive work + relayout) so the next `describe_tree`
  observes the updated state.
- **CLI clients** (`dev/client.py`, `dev/__main__.py`). `describe-tree`,
  `screenshot`, `click`, `type`, and `key` are one-shot subcommands that discover
  the running app and issue plain HTTP, dependency-free (`urllib`).

### 12.1 MCP server ([#376](https://github.com/yuksblog/nuiitivet/issues/376))

`dev/mcp_server.py` is the MCP-host-facing surface over the same bridge: it
exposes `describe_tree`, `screenshot`, `click`, `type`, and `key` as MCP tools so
any host (Claude Desktop, IDE integrations, other agents) — not just a shell with
the CLI — can drive a running app. It holds no app logic; each tool forwards to a
freshly discovered `BridgeClient`, inheriting the bridge's dev-session gate. The
`mcp` SDK is an optional dependency (the `[mcp]` extra); importing the module
without it raises a `MissingMCPDependencyError` pointing at
`pip install 'nuiitivet[mcp]'`.

**Usage guidance is part of the surface.** The server and tool descriptions steer
the model to default to `describe_tree` for reasoning and target resolution (a
cheap JSON tree) and to reserve `screenshot` for occasional visual spot checks,
because image tokens are expensive.

Served over stdio (the transport every MCP host supports):

```
python -m nuiitivet.dev mcp        # serve the running app's bridge as MCP tools
```

MCP host config (the app itself is launched separately with
`python -m nuiitivet.dev yourapp/app.py`):

```json
{
  "mcpServers": {
    "nuiitivet-dev": {
      "command": "python",
      "args": ["-m", "nuiitivet.dev", "mcp"]
    }
  }
}
```

The server starts even when no app is running; each tool call then reports a
"no running app" error until one is up, so a host may launch the server first.

## 13. Implementation map

| Design area | Module |
| --- | --- |
| dev-session detection / handoff | `App.run()` (`runtime/app.py`) → `dev/session.py` |
| factory-accepting `content` | `App.__init__` / `RootFactory` (`runtime/app.py`) |
| content-subtree rebuild/commit | `App._rebuild_content_root` / `_commit_content_root` |
| launch-target resolution (path / `--module`) | `dev/loader.py` |
| user-module identification | `dev/reloader.py` (`identify_user_modules`) |
| dependency-ordered reload + `.pyc` invalidation | `dev/reloader.py` (`_topological_order`, `reload_user_modules`) |
| state snapshot / restore | `dev/snapshot.py` |
| file watching (background thread → UI thread) | `dev/watcher.py` + `dev/controller.py` |
| error resilience | `dev/error_overlay.py` |
| CLI entry / startup flow | `dev/__main__.py` |
| dev bridge (localhost, UI-thread marshalling, discovery) | `dev/bridge.py` + `dev/client.py` |
| perception (`describe_tree` / `screenshot`) | `dev/perception.py` |
| action (`click` / `type` / `key`, target resolution) | `dev/action.py` |
| MCP server (bridge as MCP tools, stdio) | `dev/mcp_server.py` |
