# Dev Bridge MCP

Hot reload lets *you* edit a running app; the **dev bridge** lets a **coding
agent** see and drive that same app — read the widget tree, click, scroll
and type, wait for async work to settle, and catch up on what you did between
its turns. After a change it checks the result itself, so you are not the one
who has to.

The bridge is a localhost-only HTTP server that the dev runner starts alongside
hot reload. It **refuses to start without an active dev session**, so it is never
opened in a production build.

## Quick start

### 1. Install the dev extra

The MCP server ships as an optional dependency:

```bash
pip install 'nuiitivet[dev]'
```

### 2. Register the server in your MCP host

If you installed the skills through the Claude Code plugin
([install options](install_skills.md#install-through-the-claude-code-plugin)), skip this step — the
plugin registers this server for you.

`python -m nuiitivet.dev mcp` serves the bridge's primitives as MCP tools over
stdio. Register that command:

```json
{
  "mcpServers": {
    "nuiitivet-dev": {
      "command": ".venv/bin/python",
      "args": ["-m", "nuiitivet.dev", "mcp"]
    }
  }
}
```

The project-relative `command` pins the server to your project's environment,
so it works no matter how the MCP host was launched. It resolves from where
the host starts the server — the project root, for Claude Code; on Windows the
path is `.venv\Scripts\python.exe`. A plain `python` also works, but only when
the host is launched with the right environment already on PATH.

### 3. Launch your app under the dev runner

```bash
python -m nuiitivet.dev run path/to/app.py
```

The bridge starts with the app. This is a separate process from step 2 — that
entry only serves the tools. The two are independent: the MCP server starts even
with no app running, and each tool call reports a "no running app" error until
one is up, so the order of steps 2 and 3 does not matter.

### 4. Confirm the connection

Run `python -m nuiitivet.dev status`, or ask the agent to call `status`. It
is the cheapest tool and reports the running app's window title, so a successful
call confirms both that the bridge was reached and that it found the app you
meant.

Everything below assumes this setup is in place.

## What the agent can do

It reads the running app as a tree of widgets with their state, and as the
live `Observable` values behind them. It drives the app by clicking, scrolling,
typing and pressing keys on a widget it names, then waits for async work before
it reads again. It reads three logs — your hot reloads, what you did in the app,
and the app's own errors — and the comments you
[wrote on the app](on_screen_modes.md#write-instructions-on-the-app-comment-mode).
Which tool it reaches for, and when, is the `nuiitivet-debug` skill's business.

What is worth knowing as the human in the loop:

- **What you type is never recorded.** The log of your actions keeps clicks,
  shortcut keys and scrolls; a burst of typing collapses to one content-free
  marker, so field text never leaks.
- **A comment is the one thing that runs from you to the agent.** Everything
  else reports what the app is; a comment reports what you *mean*.
- **A silent failure surfaces in the app's error log.** A handler that raises is
  swallowed to keep the app alive, so the screen looks unchanged; the agent
  finds the traceback there, and so can you: `python -m nuiitivet.dev runtime-log`.
- **Its screenshot is not a capture of your window.** It re-renders the widget
  tree, so your screen can be visibly garbled while its image comes back clean.
  For a problem *you* are seeing, send it your own screenshot.
- **"Blank screen" is a heuristic.** The health check flags a frame of one
  uniform colour, which catches a paint that raised — and an intentionally
  solid screen too.
- **Profiling is not free.** While the agent records rebuilds and frame
  timings, frames run roughly 10% slower; outside a recording nothing is
  installed and nothing costs anything.

## Watch the agent act (on-screen)

`interaction_log` closes the loop in one direction — it lets the agent catch
up on what *you* did. The **action overlay** closes the reverse direction: it
lets *you* see what the *agent* is doing. When the agent drives the app
the screen updates on its own, and without the overlay you cannot tell at a
glance which action caused it. Each verb draws a short-lived marker:

| Action | What you see |
| --- | --- |
| `click` | A pulse at the resolved target, plus its `key` / `label`. A raw-coordinate click shows a bare point instead. |
| `scroll` / `scroll_into_view` | A chevron drifting along the scroll direction as it fades, captioned in words (`scroll down feed`). Both draw the same marker — what you need to see is that the view moved. |
| `type` | A caret marker near the focused widget. <br> **The typed content is never drawn**, consistent with `interaction_log`, so it cannot leak into a screenshot either. |
| `key` | The keystroke as a human-readable combo (e.g. `Ctrl+Enter`), in the corner caption stack. |

These markers are **indigo**; comment mode's are **amber**; layout edit mode's ghosts
are **teal**; the source jump's brackets are **rose**. What the agent did,
what you pointed at, what is about to change in your file, and where a click
would take you must never be confusable.

## No MCP host? Use the CLI

Some environments have no MCP host. The same primitives are available as one-shot
CLI subcommands that discover the running app and issue plain HTTP — dependency
free (standard-library `urllib` only), no `[dev]` extra required:

```bash
python -m nuiitivet.dev status
python -m nuiitivet.dev describe-tree
python -m nuiitivet.dev describe-state
python -m nuiitivet.dev describe-state --include-animations
python -m nuiitivet.dev see-comments
python -m nuiitivet.dev reload-log
python -m nuiitivet.dev interaction-log
python -m nuiitivet.dev runtime-log
python -m nuiitivet.dev runtime-log --verbose on
python -m nuiitivet.dev profile start
python -m nuiitivet.dev profile stop
python -m nuiitivet.dev screenshot -o out.png
python -m nuiitivet.dev screenshot --key save -o save.png   # one widget, padded 8px
python -m nuiitivet.dev screenshot --rect 100 50 80 40      # a raw region
python -m nuiitivet.dev click --label increment
python -m nuiitivet.dev scroll --key feed --dy 5      # --key names the region
python -m nuiitivet.dev scroll --xy 238 367 --dy 5    # ...or its rect centre
python -m nuiitivet.dev scroll-into-view --key row-42
python -m nuiitivet.dev scroll-into-view --label Done --align center
python -m nuiitivet.dev type "hello"
python -m nuiitivet.dev key enter --mod accel
python -m nuiitivet.dev wait-for --label Done
python -m nuiitivet.dev wait-for --key spinner --absent --timeout 5
```

Each subcommand talks to an already-running `python -m nuiitivet.dev run <app.py>`
process over localhost. If none is found, it says so and exits.

### Addressing a secondary window

Everything above addresses the main window. An app with more than one window
lists them under `status`, and the subcommands that reach a window —
`describe-tree`, `describe-state`, `screenshot`, `click`, `scroll`,
`scroll-into-view`, `type`, `key`, `wait-for` — take `--window <id>` to pick one:

```bash
python -m nuiitivet.dev status                       # {"windows": [{"id": 1, ...}, {"id": 2, ...}]}
python -m nuiitivet.dev describe-tree --window 2
python -m nuiitivet.dev click --key close --window 2
```

An id no open window answers to fails with that reason rather than quietly
falling back to the main window. The MCP tools take the same ids as a `window`
argument.

## Safety

- **Localhost-only.** The server binds an ephemeral port on localhost and
  publishes it to `<project_root>/.nuiitivet/dev-bridge.json` for clients to
  discover.
- **Dev-session gated.** The bridge refuses to start unless the dev runner
  installed a dev session, so it cannot be opened by a production launch
  (`python -m yourpkg`).
- **Never shipped.** There is no dev/prod branching in your code; the bridge
  lives entirely inside the dev runner.

## Next Steps

- [AI pair-programming](index.md) — the section overview.
