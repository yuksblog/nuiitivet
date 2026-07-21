# Dev Bridge MCP

Hot reload lets *you* edit a running app; the **dev bridge** lets an **AI
assistant** see and drive that same app — read the widget tree, screenshot it,
click and type, wait for async work to settle, and catch up on what you did
between its turns. It is the perception–action half of the
[AI pair-programming](index.md) loop.

The bridge is a localhost-only HTTP server that the dev runner starts alongside
hot reload. It **refuses to start without an active dev session**, so it is never
opened in a production build. Everything below assumes your app is already
running under the dev runner:

```bash
python -m nuiitivet.dev path/to/app.py
```

## Connect an MCP host

The recommended way to reach the bridge is over **MCP** — the assistant calls the
bridge's primitives as MCP tools. Serve them over stdio:

```bash
python -m nuiitivet.dev mcp
```

The MCP server ships as an optional dependency. Install the extra once:

```bash
pip install 'nuiitivet[mcp]'
```

Then register the server in your MCP host. The app itself is launched
separately (with `python -m nuiitivet.dev path/to/app.py`); this entry only
serves the bridge:

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
"no running app" error until one is up, so a host may launch the server first
and you can start the app whenever you like.

## What the assistant can do

The bridge exposes eleven tools, split across the loop.

There are three ways to "check the app", cheapest first — reach for them in this
order rather than defaulting to a screenshot:

- **Is it up and healthy?** → `status` (below) — no tree, no image.
- **Is the right thing on screen?** → `describe_tree` — the structure, cheap in
  tokens.
- **Do the pixels look right?** → `screenshot` — a last resort for genuine
  visual/layout checks; image tokens are expensive.

### Check it's up

- **`status`** — the cheapest health check, and the first thing to call after
  starting the app or after an edit. It returns, without the tree or an image:
  `running` (always `true` when the call succeeds — a stopped app fails the call
  instead), `title` (the current window title, so you can confirm *which* app is
  running), `last_reload` (`{"seq", "outcome"}` of the newest hot-reload, so
  `outcome: "error"` tells you the last save did not compile), `error_count` (the
  number of retained `ERROR`/`CRITICAL` runtime events — nonzero means something
  failed at runtime), and `blank` (`true` when the frame is a single uniform
  color — a **white/blank screen** where nothing painted). `blank` is the one
  signal the tree cannot give: the tree can look right while a swallowed paint
  exception leaves the screen blank, and `status` catches that without a
  screenshot. It is a heuristic — an intentionally solid-color screen also reads
  blank.

### See

- **`describe_tree`** — walks the mounted tree into compact JSON: each node's
  type, human identity (`key` / `label` / `text` / `title`), and rect
  `[x, y, w, h]` in root coordinates. This is the low-token view the assistant
  reasons over and resolves action targets from. Use it to check the right thing
  is on screen and to target actions — prefer it over a screenshot for
  everything except a genuine visual check.
- **`describe_state`** — the reactive companion to `describe_tree`. Where the
  tree is the *output*, this is the *state that produced it*: the live
  `Observable` values reachable from the mounted tree. It returns the same nested
  shape as `describe_tree` — pruned to nodes that hold state (or contain one that
  does) — so the two views join node-for-node by type and identity. Each node's
  `state` maps a name to its current value (e.g. `{"checked": true}`); a
  derived/computed value is instead `{"value", "kind": "computed"}`. Reach for it
  when the tree looks right but behaves wrong, or looks wrong but the code seems
  right — the classic "the value updated but the UI didn't" (or the reverse)
  reactive bug, where the tree alone cannot tell you which side is at fault.
- **`screenshot`** — renders the current frame to PNG. A **last resort**, only
  when you genuinely need to see pixels — a visual or layout check the structure
  cannot express; image tokens are expensive. Do not reach for it to confirm the
  app started or is healthy (`status` answers that, and its `blank` flag already
  catches a white screen) or to read on-screen structure (`describe_tree`).

### Act

- **`click`** / **`type`** / **`key`** — synthesize the same input the real
  backend delivers. Targeting is by **stable identifier** (`key` / `label`),
  resolved to the widget's centre, so it survives layout changes; raw
  coordinates are a fallback. Attach a `key` to a widget with the
  [`keyed()` modifier](../modifiers/others.md#keyed). Each verb settles the app (flushes reactive work
  and relayout) before returning, so the next `describe_tree` observes the
  updated state.

### Wait

The settle each action does flushes **synchronous** reactive work and relayout —
it does *not* wait for **asynchronous** work (network, timers, `asyncio` tasks,
multi-frame animations). As soon as an action kicks off async loading, an
immediate `describe_tree` can race it and observe a spinner or a stale tree, not
the finished result.

- **`wait_for`** — bridges that gap. Name a condition over the tree by `key`,
  `label`, and/or `text` (a substring of a visible identity); the bridge polls —
  re-settling each time — until it holds or `timeout` seconds elapse (default
  `3.0`). Because the poll loop lives on the bridge's worker thread and only
  briefly hops the UI thread per check, the app's own async work keeps advancing
  between polls, so the condition can actually become true. Set `present=False`
  to wait for a target to **disappear** (e.g. a loading spinner clearing).

  It returns `{"satisfied", "timed_out", "waited", "polls", "condition"}`. A
  plain timeout is reported as `satisfied: false` — **not** an error — so the
  assistant follows up with `describe_tree` to see the state the app actually
  reached. **Animations are waited *out*, not skipped**: `wait_for` only reports
  satisfied once the predicate holds on a settled frame, so a value mid-transition
  is not mistaken for its final state.

  There is deliberately **no** `assert` or `tree-diff` tool. An assistant already
  reads the whole tree with `describe_tree` and can verify an expectation or diff
  two snapshots by reasoning over it; a built-in assert/diff would only duplicate
  that at the cost of a larger tool surface. `wait_for` earns its place because
  *waiting* for async work is the one thing the assistant cannot synthesize from
  a single tree read.

### Catch up on your turn

The bridge is AI-initiated: the assistant sees its own turns, not what *you* did
between them. Two pull-able logs close that gap.

- **`reload_log`** — the reloads your saves triggered, each as success (with the
  reloaded module names) or error (with the traceback). A per-file-hash
  `changed` list marks which files' source *actually* changed, so a no-op save
  (an editor autosave that bumped mtime without changing bytes) is
  distinguishable from a real edit. A monotonic `seq` lets the assistant tell
  whether anything reloaded since its last turn.
- **`interaction_log`** — the coarse UI actions *you* took while the assistant
  was mid-task: a `click` resolved to a widget identity, a shortcut/navigation
  `key`, and a content-free `text` marker. It mirrors the action vocabulary, so
  the assistant can replay how you reached the current screen. **Typed content
  never enters it** — a bare printable keystroke is dropped and a burst of typing
  collapses to one marker, so field text never leaks.

### See why an action did nothing

`describe_tree` shows the tree *after* an action — but when the assistant drives
a `click` / `type` / `key` and the callback it triggers **raises**, the framework
swallows the exception to keep the app alive (a broken handler must not tear down
the window). The tree then looks unchanged and the traceback goes to a console
the assistant cannot read: it can see *that* nothing happened, not *why*.

- **`runtime_log`** — the running app's recent log output and uncaught
  exceptions, oldest-first. Each event is `{"seq", "timestamp", "level",
  "source", "thread", "message", …}` with an optional `exc_type` / `traceback`
  when it carries a failure. `source` distinguishes a captured `logging` record
  from an uncaught exception on a background `thread` or via the main-thread
  `excepthook`, and `thread` names where it happened — so a UI-thread callback
  error, a crashed worker thread, and an unretrieved asyncio task exception are
  all visible through one surface. A monotonic `seq` lets the assistant tell what
  is new since its last turn.

  Repeated identical failures **collapse to one entry** by default, so a handler
  that raises every frame cannot bury the rest of the log. When a collapsed entry
  is hiding a distinct error you are chasing, **`set_runtime_log_verbose(True)`**
  turns de-duplication off process-wide so every occurrence is recorded; call it
  with `False` to restore the quiet default.

## Watch the assistant act (on-screen)

`interaction_log` closes the loop in one direction — it lets the assistant catch
up on what *you* did. The **action overlay** closes the reverse direction: it
lets *you* see what the *assistant* is doing. When the assistant drives the app,
hot reload makes the screen update on its own, but without the overlay you cannot
tell at a glance which action caused it. The overlay draws a short-lived,
human-only marker for each verb:

- **`click`** — a pulse at the resolved target, plus the target's
  `key` / `label`. A raw-coordinate click shows a bare point.
- **`type`** — a caret marker near the focused widget. The **typed content is
  never drawn** (consistent with `interaction_log`, and so it never leaks into a
  screenshot).
- **`key`** — the keystroke, rendered as a human-readable combo (e.g.
  `Ctrl+Enter`), in the corner caption stack.

Each marker fades on its own timeline, so actions that fire in quick succession
(a scripted CLI loop) accumulate into a readable **trail** rather than replacing
one another. An ordered caption stack in the bottom-left corner keeps the
sequence legible even when the spatial markers overlap.

The overlay is **for the human only** and never enters the assistant's
perception:

- Markers live outside the widget tree, so `describe_tree` never sees them.
- They are painted only on the live on-screen frame and are **excluded from
  `screenshot`**, so the assistant never sees its own residue nor pays image
  tokens for it.

It is on by default in a dev session and is a no-op under headless / automated
runs. Set `NUIITIVET_DEV_ACTION_OVERLAY=0` to turn it off.

## No MCP host? Use the CLI

Some environments have no MCP host. The same primitives are available as one-shot
CLI subcommands that discover the running app and issue plain HTTP — dependency
free (standard-library `urllib` only), no `[mcp]` extra required:

```bash
python -m nuiitivet.dev status
python -m nuiitivet.dev describe-tree
python -m nuiitivet.dev describe-state
python -m nuiitivet.dev reload-log
python -m nuiitivet.dev interaction-log
python -m nuiitivet.dev runtime-log
python -m nuiitivet.dev runtime-log --verbose on
python -m nuiitivet.dev screenshot -o out.png
python -m nuiitivet.dev click --label increment
python -m nuiitivet.dev type "hello"
python -m nuiitivet.dev key enter --mod accel
python -m nuiitivet.dev wait-for --label Done
python -m nuiitivet.dev wait-for --key spinner --absent --timeout 5
```

Each subcommand talks to an already-running `python -m nuiitivet.dev <app.py>`
process over localhost. If none is found, it says so and exits.

## Safety

- **Localhost-only.** The server binds an ephemeral port on localhost and
  publishes it to `<project_root>/.nuiitivet/dev-bridge.json` for clients to
  discover.
- **Dev-session gated.** The bridge refuses to start unless the dev runner
  installed a dev session, so it cannot be opened by a production launch
  (`python -m yourpkg`).
- **Never shipped.** There is no dev/prod branching in your code; the bridge
  lives entirely inside the dev runner.

## See also

- [AI pair-programming](index.md) — the full edit → see → act loop
  this bridge is one half of.
- [Hot Reload](hot_reload.md) — the other half: how saves rebuild the running
  tree.
