# The dev bridge

The dev bridge lets a coding agent see and drive your running app, and
check its own change. [Set up](setup.md#3-register-the-mcp-server) registers
its MCP server with your agent. From then on, every tool call reaches the app
you have running.

## Let it check its own change

Ask for a change, in chat or on a mark: "make the counter's button wider".
The agent edits the file, your window reloads, and the agent reads the
widget tree back and clicks the button before it answers. Your own clicks
and keys in the app, the reloads and the app's errors are logs it reads too.

## Know what it sees of you

- **What you type is never recorded.** The log of your actions keeps clicks,
  shortcut keys and scrolls. A burst of typing collapses to one content-free
  marker.
- **Only your comments reach the agent in your words.** It answers on the
  mark, and you reply there.

## Know what to expect from it

- **A handler that raises leaves the screen unchanged.** The agent finds the
  traceback in the app's error log, and so can you:
  `python -m nuiitivet.dev runtime-log`.
- **Its screenshot is not a capture of your window.** Your screen can be
  visibly garbled while its image comes back clean. For a problem *you* are
  seeing, send it your own screenshot.
- **The health check flags any single-colour frame as blank**, an
  intentionally solid screen too.
- **Profiling slows frames by roughly 10% while it records.** No cost outside
  a recording.
- **It never runs in production.** The bridge lives inside the dev runner.
  `python app.py` opens no port.

## Watch it act on screen

The **action overlay** marks each action the agent takes on your screen. It
is on under the dev runner. `NUIITIVET_DEV_ACTION_OVERLAY=0` turns it off.
Its markers are **indigo**; comment mode's are amber.

## Drive the app without an MCP host

The same primitives are one-shot CLI subcommands. They need no `[dev]` extra:

```bash
python -m nuiitivet.dev status
python -m nuiitivet.dev describe-tree
python -m nuiitivet.dev click --label increment
```

Each subcommand talks to an already-running `python -m nuiitivet.dev run <app.py>`
process over localhost. If none is found, it says so and exits.

### Address a secondary window

An app with more than one window lists them under `status`, and the
subcommands that reach a window — `describe-tree`, `describe-state`,
`screenshot`, `click`, `scroll`, `scroll-into-view`, `type`, `key`,
`wait-for` — take `--window <id>` to pick one:

```bash
python -m nuiitivet.dev status                       # {"windows": [{"id": 1, ...}, {"id": 2, ...}]}
python -m nuiitivet.dev describe-tree --window 2
python -m nuiitivet.dev click --key close --window 2
```

An id no open window answers to fails with that reason rather than quietly
falling back to the main window. The MCP tools take the same ids as a `window`
argument.

## Every marker

| Action | What you see |
| --- | --- |
| `click` | A pulse at the resolved target, plus its `key` / `label`. A raw-coordinate click shows a bare point instead. |
| `scroll` / `scroll_into_view` | A chevron drifting along the scroll direction as it fades, captioned in words (`scroll down feed`). |
| `type` | A caret marker near the focused widget. The typed content is never drawn. |
| `key` | The keystroke as a human-readable combo (e.g. `Ctrl+Enter`), in the corner caption stack. |

## Every command

```bash
python -m nuiitivet.dev status
python -m nuiitivet.dev describe-tree
python -m nuiitivet.dev describe-state
python -m nuiitivet.dev describe-state --include-animations
python -m nuiitivet.dev see-comments
python -m nuiitivet.dev answer-comments 2 done "widened to 240"
python -m nuiitivet.dev wait-comments                     # one line per Send, until the app stops
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

## Next Steps

- [With a coding agent](index.md) — the section overview.
