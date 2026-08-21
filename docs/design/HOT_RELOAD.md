# Hot Reload

> Status: Implemented
> Related: [#359](https://github.com/yuksblog/nuiitivet/issues/359)
> User guide: [docs/guide/ai_pair_programming/hot_reload.md](../guide/ai_pair_programming/hot_reload.md)

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
   structural path (§7.4), and the declarative navigation stack (§7.5).
2. **Reload** the user's modules in dependency order (§7.1–7.2) and re-fetch the
   factory (§7.3).
3. **Rebuild** the content root (`_rebuild_content_root`), which also resets the
   global Navigator/Overlay roots.
4. **Restore** snapshot values into the matching observables of the new tree and
   replay the navigation stack onto the rebuilt navigator (§7.5).
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

### 7.5 Navigation stack restore

The rebuilt tree starts a fresh `Navigator` at its initial route, so pushed
routes would be lost. For **declarative** navigation the stack is instead
snapshotted and replayed, mirroring the `Observable` restore above (#378):

- The navigator logs a **restore descriptor** for every route added via `push`.
  A declarative push — `push(SomeIntent(...))` against a
  `Navigator.intents(...)` / `Navigator.routes(...)` route table — records the
  intent *value* plus its type's fully-qualified name. An imperative push of a
  raw `Route`/`Widget` instance records an **opaque** marker: it was built from
  the old code with no factory to rebuild it, so it is not restorable (the same
  instance-vs-factory constraint as the root, §7.3). The log tracks only pushed
  routes; the initial construction stack is rebuilt by the factory.
- Before the swap, `snapshot_navigation()` reads the root navigator's log. After
  the commit, `restore_navigation()` replays each descriptor onto the freshly
  built navigator, resolving the intent **by qualified name** — reloading
  redefines the intent class, so the live `type(intent)` no longer equals the
  new route-table key; matching on the qualified name bridges the old value to
  the new builder. Each restored route is pushed without animation.
- Replay **stops at the first non-restorable entry** — an opaque push, or an
  intent whose route is no longer registered — leaving the rest collapsed. This
  is the documented degradation, analogous to unmatched `Observable` paths.
- Open overlays/dialogs are out of scope and keep resetting (§11): they are
  transient UI bound to an in-flight awaited coroutine, and dropping that
  continuation is the safe default (Flutter behaves the same).

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
- **Declarative navigation stack is restored; imperative pushes and open
  overlays reset.** A reload replays the **declarative** navigation stack —
  routes pushed as intents against a route table — onto the rebuilt navigator
  (§7.5, [#378](https://github.com/yuksblog/nuiitivet/issues/378)). Imperative
  instance-based `push(Screen())` is fundamentally unrestorable (same
  instance-vs-factory constraint as the root); it is recorded as opaque and
  stops the replay, leaving routes above it collapsed. A fresh `Overlay` is
  rebuilt too, so open dialogs are dropped — they are transient and bound to an
  in-flight awaited coroutine, so resetting them is the intended, safe default.
- **Module-level state is not restored** (§7.4).
- **The interaction journal (§12) records only the action-verb primitives.** It
  deliberately mirrors `click` / `key` / `text` / `scroll` and leaves higher-level *semantic*
  events (navigate / dialog open-close / submit) unrecorded, since they are
  derivable from a click sequence plus `describe_tree`. Promoting selected
  semantic events to first-class entries, and deciding whether to unify the reload
  and interaction journals under one `recent_activity` surface, are the open
  follow-ups from [#390](https://github.com/yuksblog/nuiitivet/issues/390).
- **The interaction journal is wired at the pyglet backend's input handlers.** A
  second backend would need to drive the same `InteractionRecorder` from its own
  real-input path; the recorder and journal themselves are backend-agnostic.

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
- **Perception** (`_interaction/perception.py`, #374). `describe_tree` walks the mounted
  tree into compact JSON — per node its type, human identity (`key` / `label` /
  `text` / `title`) and `rect` `[x, y, w, h]` in root coordinates. This is the
  semantic, low-token view a tool reasons over and resolves action targets from.
  `screenshot` renders the mounted tree to PNG on an offscreen raster surface
  (`_render_snapshot(for_display=False)`) rather than reading back the
  framebuffer, so defects in the GPU path or the swap chain never appear in it.
- **State perception** (`_interaction/perception.py`, [#410](https://github.com/yuksblog/nuiitivet/issues/410)).
  `describe_tree` reports the *output* — the widget tree — but not the reactive
  state that produced it, and "the value updated but the UI didn't" (or the
  reverse) is exactly the bug the tree alone cannot diagnose. `describe_state`
  walks the *same* mounted tree and reports the live `Observable` values reachable
  from it: it scans each widget's `__dict__` for observable-valued attributes
  (both the `_obs_<name>` descriptor storage and directly-assigned bindings — the
  same in-tree observables the reload snapshot preserves, §8), served pull-ably at
  `GET /describe_state`. The result mirrors `describe_tree`'s nested shape — pruned
  to nodes that hold state or contain one that does — so the two views join
  node-for-node by type and identity. A mutable source observable reports its
  current value directly; a derived one (`compute` / `map` / `combine`) is
  `{"value", "kind": "computed"}`. Values are length- and depth-capped and opaque
  objects render as `type: repr`, so no single value can bloat or break the dump.
  `Animatable` attributes are excluded by default
  ([#418](https://github.com/yuksblog/nuiitivet/issues/418)): framework animation
  state lives exclusively in that class, so the filter is one `isinstance` check
  and needs no name matching, and it runs *before* pruning so a widget left with
  only animation channels prunes away instead of surviving as a hollow node.
  `include_animations=True` (`?include_animations=1` on the endpoint) opts back
  in, for when an animation is itself the bug.
  Read-only: poking values (`set_state`) is deliberately out of scope. Because
  semantic widget state (`Checkbox.checked`, text-field value, toggles) is already
  `Observable`-backed, this surfaces it automatically.
- **Action** (`_interaction/action.py`, [#375](https://github.com/yuksblog/nuiitivet/issues/375)).
  `click` / `type` / `key` synthesize the same input the real backend delivers.
  Targeting is by *stable identifier* (`key` / `label`), resolved to a rect
  centre, so it survives layout changes; raw coordinates are a fallback. Every
  verb `settle`s (flush reactive work + relayout) so the next `describe_tree`
  observes the updated state.
- **Reload journal** (`dev/journal.py`, [#388](https://github.com/yuksblog/nuiitivet/issues/388)).
  The bridge is AI-initiated — the assistant reads and acts on its own turns and
  cannot see what the *human* did between them. In a pair session the human edits
  and saves while the assistant is mid-task, so its cached `describe_tree` and its
  assumptions about the source go stale; the worst case is a *failed* reload,
  where the previous UI keeps running against code the assistant is no longer
  reading. The controller records each reload — success (with the reloaded module
  names) or error (with the capped traceback) — into a bounded, thread-safe ring
  buffer (`ReloadJournal`, one shared instance injected into both the controller
  and the bridge). The bridge exposes it as a pull-able perception surface at
  `GET /reload_log` (optional `?limit=N`). An AI pair acts in turns, not a
  continuous attention loop, and MCP is request/response — so a pull-able log is
  the right model, not a live push. Each event carries a monotonic `seq` so a
  client can tell whether new reloads happened since its last turn, and a
  `changed` list — the modules whose *source content actually changed*, detected
  by per-file hash. The watcher fires on mtime, which an editor autosave or
  formatter bumps even when the bytes are identical, so an empty `changed` marks
  a no-op save the assistant can ignore, while a non-empty `changed` pinpoints
  which file the human edited (the reloader reloads *all* user modules on any
  change, so `modules` alone cannot). Recording the diff *content* is
  deliberately out of scope — that is a token/size firehose; the boolean-grade
  `changed` signal is the cheap middle ground.
- **Interaction journal** (`dev/interaction.py`, [#390](https://github.com/yuksblog/nuiitivet/issues/390)).
  The reload journal closes the "the *code* changed under me" gap; this closes the
  complementary one — "the *human drove the app* under me." In a pair session the
  human often reproduces a bug or navigates a screen while the assistant is
  mid-task, so its cached `describe_tree` is of a stale screen and it cannot tell
  *how* the human reached the current state. An `InteractionRecorder` attached to
  the app records the human's coarse UI actions into a bounded, thread-safe ring
  buffer (`InteractionJournal`), served pull-ably at `GET /interaction_log`
  (optional `?limit=N`) with the same monotonic-`seq` turn model as the reload
  journal. Two design choices are load-bearing:
  - **A mirror of the action vocabulary, not a semantic taxonomy.** It records
    exactly the inbound of `click` / `key` / `type` / `scroll`: a `click` resolved
    to a widget identity (`{type, key?, label?}` — reusing the same identity walk
    as perception, *never* a coordinate), a `key` (only shortcuts and navigation
    keys), a content-free `text` marker, and a `scroll` (§12.2). Whatever the human
    does that the assistant must reproduce, it reproduces *through those same
    verbs*, so this set is necessary and sufficient to replay a path — and it grows
    only when the vocabulary does. Higher-level semantic events (navigate / dialog
    open-close / submit) are deliberately *not* recorded — they are states
    derivable from a click sequence plus `describe_tree`, not primitive inputs.
  - **Recorded at the real-input layer, so the human only.** The recorder is
    driven from the backend's real input handlers (`on_mouse_press` /
    `on_key_press` / `on_text` / `on_mouse_scroll`), which the assistant's
    synthesized actions bypass (those enter below at `app._dispatch_*`). So the
    journal captures the human with no synthetic/real tagging. **Typed content
    never enters it:** a bare printable key with no command modifier is dropped
    (recording it would leak field text a keystroke at a time), and a burst of
    `on_text` collapses to one content-free marker.
- **Runtime journal** (`dev/runtime_journal.py`, `dev/runtime_capture.py`, [#409](https://github.com/yuksblog/nuiitivet/issues/409)).
  The reload and interaction journals surface what *changed* and what the human
  *did*; this surfaces what the app *emitted*. When an assistant-driven `click` /
  `type` / `key` triggers a callback that raises, the framework swallows the
  exception to keep the app alive (`invoke_event_handler`) and logs it — to a
  console the assistant, driving over MCP, cannot read. The post-action
  `describe_tree` then shows an unchanged tree: the assistant sees *that* nothing
  happened, not *why*. A `RuntimeLogCapture` installs three taps that route into a
  bounded, thread-safe `RuntimeJournal`, served pull-ably at `GET /runtime_log`
  (optional `?limit=N`) with the same monotonic-`seq` turn model as the other
  journals:
  - a **`logging.Handler`** on the root logger (WARNING+) — the primary net,
    capturing framework and app records from any thread; asyncio reports an
    unretrieved task exception by *logging* it at ERROR, so those land here too;
  - **`threading.excepthook`** and **`sys.excepthook`** — uncaught exceptions on
    a background or the main thread, which Python does not route through
    `logging`. Both chain to the previous hook, so console output is unchanged.

  De-dup is *not* in the journal; it lives at the emit sites (`logging_once`). A
  record suppressed there never reaches the handler, so by default the log shows
  each distinct failure once rather than a flood of the same one — and the
  callback boundary keys by *distinct exception* (`exception_once_per_exc`), so a
  new error from the same handler after a hot-reload fix still surfaces. A
  process-wide **verbose** switch (`POST /runtime_log/verbose`) flips
  `set_log_once_enabled(False)` so a debugging session can see every occurrence.
- **Designation** (`dev/selection.py`, `dev/inspect.py`, `dev/selection_overlay.py`,
  [#591](https://github.com/yuksblog/nuiitivet/issues/591)).
  Every surface above runs assistant → app. This one runs **human → assistant**:
  it records what the human *pointed at*. Prose is an expensive channel for a
  location, and for two cases it barely works at all — an anonymous inner node
  (no phrase identifies it) and a *gap* (no widget to name). Inspect mode is
  a latched, dev-only gesture layer sitting on the backend's *real* input
  handlers — the same layer the interaction recorder uses, and for the same
  reason: the assistant's synthesized actions enter below it at `app._dispatch_*`
  and so can never forge a designation. The bridge serves the result at
  `GET /describe_selection`, with a `selection` roll-up on `/status` and a
  content-free `select` marker on the interaction journal so an assistant
  notices it without being told. The gestures themselves are the user guide's
  business.
  - **Ownership and threading.** One `Selection` per app, built by the dev runner
    and shared three ways: `InspectMode` writes it from the UI thread,
    `HotReloadController` re-resolves it after a rebuild, and the bridge reads it
    on HTTP worker threads. It carries its own `RLock` for that last split — the
    same shape as the reload and interaction journals. Nodes and regions live in
    one ordered list because they share one on-screen numbering.
  - **Session semantics.** `enter()` snapshots the marks; `commit()` keeps what
    the session did and `discard()` restores the snapshot, so a cancel scopes to
    one session rather than to everything, and clearing is undoable because it
    happens inside one. A reload remaps the snapshot alongside the live marks —
    without that, cancelling after a rebuild would restore members whose
    referents are already gone.
  - **`pick_at`** (`_interaction/perception.py`) is the geometry-only picker.
    `hit_test` cannot serve: it returns the deepest *hit-participating* widget,
    but the node a human means is often one that participates in none (a plain
    `Text`, a spacing `Container`). Descent is narrowed through
    `focus_traversal_children()` — the same question the keyboard already asks,
    so the picker stops where the eye does — and candidates are then filtered by
    `find_obstruction`. Narrowing the *descent* rather than filtering afterwards
    is load-bearing: `find_obstruction` deliberately does not report a `None` hit
    as an obstruction (that is what keeps a non-interactive target reachable), so
    an entirely non-interactive hidden subtree — two `Text` pages in a `Deck` —
    is invisible to the occlusion check.
  - **`is_visually_empty()`** is the second half of that same gap, opted into by
    name like `visual_offset` / `visual_clip_rect`. An `Overlay` with nothing
    open stays mounted at full window size and paints nothing; it therefore
    contains every point, sits on top of the content, and is cleared by
    `find_obstruction` for the very reason above. Every App wraps its content in
    one, so without this probe the idle overlay shadows the whole app for exactly
    the non-interactive widgets picking exists to reach. `Overlay.hit_test`
    already short-circuits on `has_entries()`; this is the same answer for
    anything reading the tree geometrically rather than dispatching input.
  - **`Box.visual_clip_rect()`** closes the third instance of that same gap,
    found by pointing at a real app rather than by a spike. `Box.hit_test` has
    always honoured `clip_content`, but the clip was never published, so
    `find_obstruction` could not see it — and the occlusion check cannot cover
    for it, because a point trimmed away lands on nothing and a `None` hit is
    deliberately not an obstruction. The idiom that exposes it is ordinary: a
    decorative shape laid out far larger than its parent and clipped to a
    corner, which is how a gradient gets faked. Its layout rect then reaches
    well outside anything painted — into a neighbouring pane, or into negative
    coordinates — and both the picker and the reported rect believed it.
  - **Reporting uses `visible_rect`, not `global_visual_rect`.** "Where is this
    node" and "what of it is on screen" are different questions, and the second
    is the one a designation answers. `global_visual_rect` stays as it is: it
    positions a pointer, and an action must aim at the node's actual origin.
    `visible_rect` intersects that with every ancestor clip and is what the
    payload and the on-screen brackets both use, so the box drawn on the glass
    and the rect handed to the assistant are the same claim. A node clipped away
    entirely has no visible rect at all.
  - **Construction sites** (`dev/source.py`) answer the question that follows
    every designation: which line built this. The dev runner wraps
    `Widget.__init__` — verified as the single chokepoint, since all 142 of the
    150 `Widget` subclasses that define `__init__` call `super()` — and walks
    `f_back` to the first frame outside the package. The wrap is installed by the
    runner and never by the framework, so a production launch pays nothing at
    all, not even a flag check on the construction path. Python's runtime frames
    are what make this cheaper than Flutter's `--track-widget-creation`, which
    needs a compile-time transform to learn the same thing.
    Two properties fall out. Sites are captured at construction and a reload
    rebuilds everything, so a site can never go stale — there is no invalidation
    step to get wrong. And sites are *interned*, because they are shared far more
    than they are distinct (one helper builds fourteen cards), which turns a
    per-widget field into a pointer into a small table: 421 nodes, 144 sites.
    The payload keeps a short chain rather than one location, for the reason the
    region fields keep two: "change every tile" wants the helper and "change this
    one" wants the call site, and only the caller knows which was meant. The
    innermost frame is flagged as the single place an editor can open.
  - **The jump** (`dev/editor.py`) is `Ctrl`/`Cmd`+click, which does *not*
    designate -- reading several widgets' code in a row must not leave a mark per
    widget. It also does not leave the mode, which is only safe because the
    overlay repaints on every state change: returning from the editor shows the
    badge that says the mode is still on. Discoverability comes from the hover
    caption carrying `file:line` and the HUD listing the gesture, which is what
    let this be a modifier instead of a button -- a pressable control would need
    hit testing inside a registry that deliberately has none, and reaching it
    would move the pointer off the widget being hovered.
    The editor is launched by its own CLI, never through a shell: the command
    template is split into arguments first and the path substituted into the
    resulting tokens, so a path with spaces stays one argument and a path with
    shell metacharacters stays inert. `PATH` is consulted first and, for the
    *default* command only, the well-known VS Code install locations after it:
    that shim is an opt-in step on macOS, so an editor that is plainly installed
    is routinely unfindable -- which the first real use hit immediately. A
    command the human configured is never redirected that way, since opening a
    different program would hide the cause rather than fix it. A failure is
    shown in place of the caption, short because it has nowhere to wrap, with
    the actionable half logged; a jump that does nothing and says nothing is
    indistinguishable from a broken feature. **Success is announced the same
    way**, for a reason the numbers make plain: spawning costs this process
    ~5 ms, but the editor's own CLI takes ~1.4 s to reach an already-running
    window, because its launcher boots a Node runtime to talk to it. That second
    is unfixable from here and reads exactly like a click that did nothing, so
    the overlay says what is being opened.
    Where VS Code is installed and the platform has a URL opener, the CLI is
    skipped entirely for the **`vscode://` URL**, handed to the registered
    handler: on macOS ~95 ms against ~1400 ms, fourteen times faster, with the
    line intact. An earlier attempt at the same shortcut there,
    `open -a ... --args --goto`, was **rejected** -- LaunchServices passes
    `--args` only when it actually *launches* the application, so an
    already-running editor received the file without the line. Both were
    verified by watching where the cursor landed rather than by reading the
    documentation. The line rides inside the URL, so there is nothing for that
    rule to drop.
    The route is chosen by whether VS Code is installed, not by probing the
    scheme: probing means waiting on the opener and paying its ~95 ms on the UI
    thread for an answer that never changes. Each platform's standard opener is
    used -- `open`, `xdg-open`, and on Windows the shell API rather than a
    process, which is also the one platform where a missing handler raises
    instead of failing silently. Linux falls back to the CLI when `xdg-open` is
    absent, since a desktop without it has nothing to hand a URL to. **All three
    were confirmed against a real editor** -- the caret lands on the line, and
    the jump is fast enough to be the URL rather than the CLI. CI can check none
    of it, being headless where the question is where the cursor ended up.
    `NUIITIVET_DEV_OPEN_COMMAND` is the escape hatch if one misbehaves, and it
    outranks the URL everywhere: speed does not outrank the human's choice of
    editor.
    The URL's path is absolute, slash-separated and leading-slashed, which is
    what turns a Windows `C:\dir\app.py` into `/C:/dir/app.py`; percent-encoding
    keeps a space from ending the URL early while leaving the separators and the
    drive-letter colon intact.
  - **Reload re-resolution.** Members are held weakly and keyed on *object
    identity* (two anonymous siblings resolve to the same identity dict, so
    keying on that would make picking the second remove the first). A rebuild
    therefore evaporates them, which is the normal case rather than an edge one —
    "point at it, then have the assistant fix it" puts a reload in the middle of
    nearly every use. They are matched back by the same key-preferring structural
    path §7.4 restores state with (`snapshot.path_of` / `widgets_by_path`), and
    misses are counted in `lost` rather than shortening the list silently.
  - **Regions** (the drag gesture) are the half node picking cannot express: an
    area with no widget in it. Only the rect is stored; `container` (the
    innermost enclosing node, plus its immediate children) and `contents` are
    derived on every read. That is what carries a region across a reload with no
    restore step, and what makes it a *continuing* observation point rather than
    a single-use note. `contents` intersects rather than requiring full
    containment — humans drag rough boxes — and is scoped to `container`'s
    subtree, which is what makes intersection workable at all: `container`
    encloses the region by definition, so the ancestor chain, which trivially
    overlaps, drops out without a special case. Each entry is tagged `contained`
    or `clipped`. An empty `contents` is the signal, not a failure; `container`
    still answers.

    `contents` is a **pruned tree, not a collapsed list**, and that is the point.
    A rectangle carries two readings the geometry cannot separate: "the gap
    between these things" wants the enclosing owner, "these things" wants what
    the box crosses. An earlier form applied `find_targets`' rule — drop a match
    nested inside another match — which answers "which widget did you name?" and
    is simply a different question: a band drawn down a column reported only the
    column, the one thing the human already knew. So the two readings get one
    field each (`container` and `contents`), neither collapsed into the other,
    and the caller — which knows what the human *said* — chooses.
  - **Privacy.** A designation may carry rects and on-screen text, unlike the
    interaction journal, which records neither. That is not an inconsistency: the
    journal records *ambiently*, without item-by-item consent, while a
    designation is an explicit act of disclosure — the same ground on which
    `screenshot` may. The layering holds because the journal marker stays
    content-free and the payload is served only on an explicit
    `describe_selection`.
  - **Overlay.** Amber, against the action overlay's indigo: indigo means "the
    assistant did this", amber means "the human means this", and one visual
    language for opposite directions would mislead. Same paint-only,
    outside-the-tree, live-frames-only constraint, so `describe_tree` never sees
    it and `screenshot` never contains it.
- **CLI clients** (`dev/client.py`, `dev/__main__.py`). `describe-tree`,
  `describe-state`, `describe-selection`, `reload-log`, `interaction-log`,
  `runtime-log`, `screenshot`, `click`, `type`, and `key` are one-shot subcommands that discover the running
  app and issue plain HTTP, dependency-free (`urllib`).

### 12.1 MCP server ([#376](https://github.com/yuksblog/nuiitivet/issues/376))

`dev/mcp_server.py` is the MCP-host-facing surface over the same bridge: it
exposes `describe_tree`, `describe_state`, `describe_selection`, `reload_log`,
`interaction_log`, `runtime_log`, `set_runtime_log_verbose`, `screenshot`,
`click`, `type`, and `key` as MCP tools so any host (Claude Desktop, IDE integrations, other agents) — not
just a shell with the CLI — can drive a running app. It holds no app logic; each tool forwards to a
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

### 12.2 Scroll in the interaction journal

Scroll is the verb whose *volume* is the design problem: a wheel emits events by
the dozen per gesture, and one entry each would bury every click and key press.
Three defenses, none of them a timer:

- **Only what a region consumed.** `_dispatch_mouse_scroll` returns the handling
  widget; `None` means nothing moved, so nothing is recorded. That also inherits
  `Scrollable._handle_scroll`'s existing refusals — `ScrollPhysics.NEVER`, the
  wrong axis, `abs(delta) < 0.01` — as a trackpad-jitter deadband.
- **A gesture coalesces by replacing the tail.** A `scroll` on the same region in
  the same direction replaces the newest event instead of appending (accumulated
  delta, refreshed metrics); any other tail starts a new one. That bounds the
  count *structurally*: never more scroll events than transitions between other
  events. **No idle timeout** — "same gesture" is region plus direction, not time,
  and a timeout would restore the unbounded count for continuous reading, the case
  the coalescing exists to handle. Splitting on direction also keeps the delta
  monotonic within an event, so down-then-up cannot collapse into a net-zero entry
  reading as "did not scroll".

  "Same region" is the handler's **object identity**, not its resolved `target`:
  two keyless siblings of one type resolve alike, and merging them would sum two
  regions' deltas into an entry whose `offset` describes only the second. The
  recorder decides it (the journal never sees the widget) and holds the previous
  handler *weakly*, so tracking it pins nothing and a collected region reads as a
  different one — degrading toward an extra entry, never a wrong merge.
- **No event counter.** Accumulated notches already answer "how far".

```json
{
  "seq": 42, "timestamp": 1754476800.0, "started_at": 1754476797.5,
  "kind": "scroll",
  "target": {"type": "VerticalScrollable", "key": "feed"},
  "direction": "down", "dy": 37.0,
  "axis": "vertical", "offset": 740.0, "max_extent": 1240.0,
  "at_start": false, "at_end": false
}
```

- **Deltas are wheel notches in `scroll`'s sign convention.** The backend's
  `_normalize_scroll_delta` applies it before the handler runs, so a logged `dy`
  replays verbatim as `scroll --dy`.
- **Position over delta.** The delta says how hard the human pushed; `offset` /
  `at_end` say where they ended up. Both come from the `scroll_metrics()` the
  `scroll` action reports from, so a log entry and an action result read alike.
- **The consuming region names the gesture, not the raw input.** `axis` comes from
  its metrics and the direction from the sign of the delta *that axis* took — a
  horizontal region driven by a vertical wheel is normal (`_handle_scroll` falls
  back from `scroll_x` to `scroll_y`), and reading the wheel would mislabel it.
- **A coalesced update re-issues `seq`,** so an ongoing scroll reads as new
  activity; `started_at` keeps the gesture's beginning.

Privacy is unchanged: `resolve_target` yields a `key` / `label`, never a
coordinate, and a scroll carries no content.

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
| perception (`describe_tree` / `describe_state` / `screenshot`) | `_interaction/perception.py`, re-exported by `dev/perception.py` |
| reload journal (pull-able reload events for an AI pair) | `dev/journal.py` (recorded by `dev/controller.py`) |
| interaction journal (pull-able human UI actions for an AI pair) | `dev/interaction.py` (recorded from the backend input handlers) |
| action (`click` / `type` / `key`, target resolution) | `_interaction/action.py`, bound to the overlay observer by `dev/action.py` |
| MCP server (bridge as MCP tools, stdio) | `dev/mcp_server.py` |
