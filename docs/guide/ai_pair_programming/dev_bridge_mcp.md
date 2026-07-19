# Dev Bridge MCP

Hot reload lets *you* edit a running app; the **dev bridge** lets an **AI
assistant** see and drive that same app — read the widget tree, screenshot it,
click and type, and catch up on what you did between its turns. It is the
perception–action half of the [AI pair-programming](index.md) loop.

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

The bridge exposes seven tools, split across the loop:

### See

- **`describe_tree`** — walks the mounted tree into compact JSON: each node's
  type, human identity (`key` / `label` / `text` / `title`), and rect
  `[x, y, w, h]` in root coordinates. This is the low-token view the assistant
  reasons over and resolves action targets from. Prefer it for everything except
  a genuine visual check.
- **`screenshot`** — renders the current frame to PNG. Reserve it for occasional
  visual spot checks; image tokens are expensive.

### Act

- **`click`** / **`type`** / **`key`** — synthesize the same input the real
  backend delivers. Targeting is by **stable identifier** (`key` / `label`),
  resolved to the widget's centre, so it survives layout changes; raw
  coordinates are a fallback. Attach a `key` to a widget with the
  [`keyed()` modifier](../modifiers/others.md#keyed). Each verb settles the app (flushes reactive work
  and relayout) before returning, so the next `describe_tree` observes the
  updated state.

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

## No MCP host? Use the CLI

Some environments have no MCP host. The same primitives are available as one-shot
CLI subcommands that discover the running app and issue plain HTTP — dependency
free (standard-library `urllib` only), no `[mcp]` extra required:

```bash
python -m nuiitivet.dev describe-tree
python -m nuiitivet.dev reload-log
python -m nuiitivet.dev interaction-log
python -m nuiitivet.dev screenshot -o out.png
python -m nuiitivet.dev click --label increment
python -m nuiitivet.dev type "hello"
python -m nuiitivet.dev key enter --mod accel
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
