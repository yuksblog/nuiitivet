# Dev Bridge MCP

Hot reload lets *you* edit a running app; the **dev bridge** lets an **AI
assistant** see and drive that same app — read the widget tree, screenshot it,
click, scroll and type, wait for async work to settle, and catch up on what you did
between its turns. It supplies the perception–action half of the
[AI pair-programming](index.md) loop.

This page is the reference for the bridge itself — every tool, and what each one
returns. Getting an assistant to reach for the right tool at the right time is a
separate concern, handled by the
[`nuiitivet-debug` skill](nuiitivet_debug_skill.md).

The bridge is a localhost-only HTTP server that the dev runner starts alongside
hot reload. It **refuses to start without an active dev session**, so it is never
opened in a production build.

## Quick start

### 1. Install the MCP extra

The MCP server ships as an optional dependency:

```bash
pip install 'nuiitivet[mcp]'
```

### 2. Register the server in your MCP host

`python -m nuiitivet.dev mcp` serves the bridge's primitives as MCP tools over
stdio. Register that command:

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

### 3. Launch your app under the dev runner

```bash
python -m nuiitivet.dev path/to/app.py
```

The bridge starts with the app. This is a separate process from step 2 — that
entry only serves the tools. The two are independent: the MCP server starts even
with no app running, and each tool call reports a "no running app" error until
one is up, so the order of steps 2 and 3 does not matter.

### 4. Confirm the connection

Run `python -m nuiitivet.dev status`, or ask the assistant to call `status`. It
is the cheapest tool and reports the running app's window title, so a successful
call confirms both that the bridge was reached and that it found the app you
meant.

Everything below assumes this setup is in place.

## What the assistant can do

Fifteen tools, grouped by the question each one answers. Skim the tool names;
where a row carries a **bold note**, that is the thing worth knowing as the human
in the loop. *When* the assistant should reach for which is the
[`nuiitivet-debug` skill](nuiitivet_debug_skill.md)'s business, not yours.

### See — read the running app

| Tool | What it gives you |
| --- | --- |
| `status` | Liveness, the window title, the newest reload's outcome, a count of runtime errors, and a `blank` flag for a screen where nothing painted. No tree, no image. <br> **`blank` is a heuristic.** It catches a swallowed paint exception that the tree cannot reveal — but an intentionally solid-color screen reads blank too. |
| `describe_tree` | The mounted tree as compact JSON — each node's type, identity (`key` / `label` / `text` / `title`), and rect. The cheap view the assistant reasons over and resolves action targets from. |
| `describe_state` | The live `Observable` values behind that tree, in the same shape as `describe_tree` so the two join node-for-node. Answers "the value updated but the UI didn't", and the reverse. <br> **Animation state is omitted by default.** `Animatable` channels carry visual rather than semantic state and would dominate the dump; `include_animations=True` brings them back. |
| `screenshot` | The mounted tree rendered to PNG. <br> **Not a capture of your window.** Your screen can be visibly garbled while `screenshot` comes back clean, so it settles nothing about a problem *you* are seeing — send the assistant your own screenshot instead. |
| `describe_selection` | The widgets and areas *you* pointed at — see [Point at something](#point-at-something-inspect-mode). Each carries a `describe_tree` / `describe_state` dump scoped to it. <br> **The only tool that runs from you to the assistant.** Everything else reports what the app is; this reports what you *meant*. |

### Act — drive it

Targeting is by **stable identifier** (`key` / `label`) — attach one with the
[`keyed()` modifier](../modifiers/others.md#keyed) — resolved to the widget's
centre *as painted*, so it survives layout changes and scrolling; raw `x` / `y`
coordinates are a fallback. A verb **refuses an unreachable target**: a widget
scrolled out of its region or covered by a modal fails with a "not visible"
error rather than delivering the event to whatever sits at those coordinates.
Each verb then settles *synchronous* reactive work and relayout before
returning — async work is what `wait_for` is for.

| Tool | What it does |
| --- | --- |
| `click` | A press and release at the target. |
| `scroll` | A wheel event over a scroll **region**. `dx` / `dy` are wheel notches (20 px each), positive toward the content's end; the reply's `at_end` is the only stop condition a scroll loop has. |
| `scroll_into_view` | Brings a target inside its region in one shot, nested regions included. `align` picks where it lands (`nearest` / `start` / `center` / `end`). |
| `type` | Injects text into the focused widget — focus one first, or `handled` comes back `false`. |
| `key` | A key press and release with optional modifiers (`shift`, `ctrl`, `alt`, `meta`, or `accel` for the platform Ctrl/Cmd). |
| `wait_for` | Polls until a condition over the tree holds, or `timeout` (default `3.0` s) elapses. `present=False` waits for a target to *disappear* — a spinner clearing. <br> **A timeout is not an error.** It returns `satisfied: false`. Animations are waited *out*, not skipped: the condition must hold on a settled frame, so a mid-transition value is never mistaken for the final one. <br> The gap between polls adapts to what a poll costs — a slow tree backs the loop off, a fast one gets many more attempts — so `polls` and `waited` describe the effort spent, not a fixed cadence. Its floor is 5 ms; `BridgeClient.wait_for(min_interval=…)` raises it. |

### Logs — catch up and diagnose

The bridge is AI-initiated: the assistant sees its own turns, not what *you* did
between them, and not what the app wrote to a console it cannot read.

| Tool | What it gives you |
| --- | --- |
| `reload_log` | The reloads your saves triggered — the modules reloaded, or the traceback that failed. A per-file-hash `changed` list separates a real edit from a no-op autosave that only bumped mtime. |
| `interaction_log` | The coarse UI actions *you* took mid-task: clicks resolved to a widget identity, shortcut keys, scrolls (with where the region ended up), and content-free text markers. <br> **Typed content never enters it.** A bare printable keystroke is dropped and a burst of typing collapses to one marker, so field text never leaks. |
| `runtime_log` | The app's recent log output and uncaught exceptions, with `exc_type` / `traceback` when one carries a failure — background threads and unretrieved asyncio tasks included. <br> **This is where a silent failure surfaces.** A handler that raises is swallowed to keep the app alive, so the tree looks unchanged and only this log says why. Repeated identical failures collapse to one entry. |
| `set_runtime_log_verbose` | Turns `runtime_log`'s de-duplication off process-wide — every occurrence of a repeated failure is then recorded — and back on. |

## Point at something (inspect mode)

Every tool above runs assistant → app. Inspect mode runs the other way: it is how
you **point**.

Prose is a poor way to name a location, and for two cases it barely works — an
inner widget with no `key` and no distinctive text, and a *gap*, where nothing
painted and there is no widget to name at all.

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+C` | Enter inspect mode (`Cmd+Shift+C` on macOS — either accelerator works throughout). The shortcut Chrome DevTools uses. |
| Click | Designate the widget under the cursor; click it again to remove it. |
| Drag | Designate an **area** instead — a gap, a misaligned band, anywhere with no widget to name. |
| `↑` / `↓` | Move the newest widget designation up to its parent, or back down, when the click landed one level off. |
| `Backspace` | Remove the newest designation. |
| `Ctrl+Backspace` | Remove them all. |
| `Enter` | Keep them and leave. |
| `Esc` | Discard this session and leave. Anything you kept with `Enter` earlier stays. |

Every designation and both removals take effect *inside* the session, so `Esc`
undoes any of them.

While the mode is on your clicks go to the picker, not the app, so you cannot
fire the button you are pointing at. A corner badge shows the mode and lists the
keys. Widgets get **corner brackets** and areas a **soft fill**, so they stay
distinct when one sits inside the other, and each carries a **numbered badge**
matching what the assistant sees — "fix the second one" is unambiguous.

You do not have to say you did it: `status` carries a `selection` summary, so the
assistant notices on the cheapest call it makes. Designations survive a reload
too, so an edit mid-conversation does not make you point again, and any that
cannot be found afterwards are reported as lost rather than quietly dropped.

Two things about areas:

- **An empty result is the answer, not a failure.** Nothing is painted there —
  and the enclosing widget names what should have been.
- **A rough box is fine.** "The gap between these" and "these things" are drawn
  the same way; both are reported, and what you *say* settles which you meant.

Only the rectangle is stored, so the assistant can re-read the same area after a
fix to see what is there now.

> **Privacy note.** `interaction_log` records neither coordinates nor typed
> content, because it records ambiently. A designation may carry both — that is
> the point of it, since you chose to show it. The journal still only gains a
> content-free marker that you designated *something*; the payload goes out only
> when the assistant asks for it.

## Watch the assistant act (on-screen)

`interaction_log` closes the loop in one direction — it lets the assistant catch
up on what *you* did. The **action overlay** closes the reverse direction: it
lets *you* see what the *assistant* is doing. When the assistant drives the app
the screen updates on its own, and without the overlay you cannot tell at a
glance which action caused it. Each verb draws a short-lived marker:

| Action | What you see |
| --- | --- |
| `click` | A pulse at the resolved target, plus its `key` / `label`. A raw-coordinate click shows a bare point instead. |
| `scroll` / `scroll_into_view` | A chevron drifting along the scroll direction as it fades, captioned in words (`scroll down feed`). Both draw the same marker — what you need to see is that the view moved. |
| `type` | A caret marker near the focused widget. <br> **The typed content is never drawn**, consistent with `interaction_log`, so it cannot leak into a screenshot either. |
| `key` | The keystroke as a human-readable combo (e.g. `Ctrl+Enter`), in the corner caption stack. |

These markers are **indigo**; inspect mode's are **amber**. The two directions
must never be confusable.

## No MCP host? Use the CLI

Some environments have no MCP host. The same primitives are available as one-shot
CLI subcommands that discover the running app and issue plain HTTP — dependency
free (standard-library `urllib` only), no `[mcp]` extra required:

```bash
python -m nuiitivet.dev status
python -m nuiitivet.dev describe-tree
python -m nuiitivet.dev describe-state
python -m nuiitivet.dev describe-state --include-animations
python -m nuiitivet.dev reload-log
python -m nuiitivet.dev interaction-log
python -m nuiitivet.dev runtime-log
python -m nuiitivet.dev runtime-log --verbose on
python -m nuiitivet.dev screenshot -o out.png
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
- [The `nuiitivet-debug` skill](nuiitivet_debug_skill.md) — the skill that teaches
  an assistant to use these tools well.
