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

### 1. Install the dev extra

The MCP server ships as an optional dependency:

```bash
pip install 'nuiitivet[dev]'
```

### 2. Register the server in your MCP host

If you installed the skills through the Claude Code plugin
([install options](nuiitivet_app_skill.md#install)), skip this step — the
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

Run `python -m nuiitivet.dev status`, or ask the assistant to call `status`. It
is the cheapest tool and reports the running app's window title, so a successful
call confirms both that the bridge was reached and that it found the app you
meant.

Everything below assumes this setup is in place.

## What the assistant can do

The tools, grouped by the question each one answers. Skim the tool names;
where a row carries a **bold note**, that is the thing worth knowing as the human
in the loop. *When* the assistant should reach for which is the
[`nuiitivet-debug` skill](nuiitivet_debug_skill.md)'s business, not yours.

### See — read the running app

| Tool | What it gives you |
| --- | --- |
| `status` | Liveness, the window title, the newest reload's outcome, a count of runtime errors, and a `blank` flag for a screen where nothing painted. No tree, no image. <br> **`blank` is a heuristic.** It catches a swallowed paint exception that the tree cannot reveal — but an intentionally solid-color screen reads blank too. |
| `describe_tree` | The mounted tree as compact JSON — each node's type, identity (`key` / `label` / `text` / `title`), interactive state (`disabled` / `focused` / `selected` / `value`), and rect. The cheap view the assistant reasons over and resolves action targets from. |
| `describe_state` | The live `Observable` values behind that tree, in the same shape as `describe_tree` so the two join node-for-node. Answers "the value updated but the UI didn't", and the reverse. <br> **These are the raw observables, under the attribute names your widgets bound them to** — `describe_tree`'s own state is the same thing in one vocabulary. <br> **Animation state is omitted by default.** `Animatable` channels carry visual rather than semantic state and would dominate the dump; `include_animations=True` brings them back. |
| `screenshot` | The mounted tree rendered to PNG — the whole frame, or just one widget: `key` / `label` crop to that widget's painted rect plus `padding` logical pixels each side (default 8, so shadows and outlines stay in), `rect=[x, y, w, h]` crops to a raw region. <br> **Not a capture of your window.** Your screen can be visibly garbled while `screenshot` comes back clean, so it settles nothing about a problem *you* are seeing — send the assistant your own screenshot instead. |
| `describe_selection` | The widgets and areas *you* pointed at — see [Point at something](#point-at-something-select-mode). Each carries a `describe_tree` / `describe_state` dump scoped to it. <br> **The only tool that runs from you to the assistant.** Everything else reports what the app is; this reports what you *meant*. |

### Act — drive it

Targeting is by **stable identifier** (`key` / `label`) — give one with the
`key=` constructor parameter every widget accepts — resolved to the widget's
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
| `key` | A key press and release with optional modifiers (`shift`, `ctrl`, `alt`, `meta`, or `accel` for the platform Ctrl/Cmd). <br> The editing keys — `backspace`, `delete`, `left`, `right`, `home`, `end` — also carry the text motion a focused text field edits on, so they delete what `type` inserted and move the caret; `shift` with one extends the selection. They stay key presses too, so the arrows still step a slider or rove a menu. |
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

### Profile — find wasted work

A start/stop recording, like a DevTools performance capture: start it, reproduce
the janky or chatty interaction, stop it and read the report. Counters are
cumulative within one recording and the session boundary is the reset — there is
no `seq` to track.

| Tool | What it gives you |
| --- | --- |
| `profile_start` | Begins recording rebuild/repaint counters and painted-frame timings. <br> **Recording is not free.** An active session inflates frame time by roughly 10% on a heavy tree; outside a session nothing is installed and nothing costs anything, so leave it off unless a question needs it. |
| `profile_stop` | Ends the recording and returns the report: painted-frame timings (mean / p95 / max of the paint walk), paint counts by widget type, and the actionable pair — scope-recomposition counts and `Observable` binding-update counts, per widget, largest first. A widget rebuilding far more often than the interaction warrants is the wasted-work signal. <br> **Paint counts track frames, not damage.** Every painted frame walks the whole tree, so per-widget paint counts equal the painted-frame count; the per-widget signal lives in the rebuild and binding counters. |

## Point at something (select mode)

Every tool above runs assistant → app. Select mode runs the other way: it is how
you **point**.

Prose is a poor way to name a location, and for two cases it barely works — an
inner widget with no `key` and no distinctive text, and a *gap*, where nothing
painted and there is no widget to name at all.

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+C` | Enter select mode (`Cmd+Shift+C` on macOS — either accelerator works throughout). The shortcut Chrome DevTools uses. |
| Click | Designate the widget under the cursor; click it again to remove it. |
| Drag | Designate an **area** instead — a gap, a misaligned band, anywhere with no widget to name. |
| `↑` / `↓` | Move the newest widget designation up to its parent, or back down, when the click landed one level off. |
| `Backspace` | Remove the newest designation. |
| `Ctrl+Backspace` | Remove them all. |
| `Enter` | Keep them and leave. |
| `Esc` | Discard this session and leave. Anything you kept with `Enter` earlier stays. |
| `Ctrl+Shift+E` | Keep them and switch to [layout mode](#resize-or-reorder-a-widget-by-dragging-layout-mode). |

Every designation and both removals take effect *inside* the session, so `Esc`
undoes any of them.

While the mode is on your clicks go to the picker, not the app, so you cannot
fire the button you are pointing at. A corner badge shows the mode and lists the
keys. Widgets get **corner brackets** and areas a **soft fill**, so they stay
distinct when one sits inside the other, and each carries a **numbered badge**
matching what the assistant sees — "fix the second one" is unambiguous.

Hovering names the widget **and the line that built it**, and the assistant is
given that same line — so it edits the right place instead of hunting for it.
That is worth most in the apps where naming a widget in prose is hardest: the
ones passing no `key=` anywhere. To open that line yourself, see
[Jump to the source](#jump-to-the-source).

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

## Resize or reorder a widget by dragging (layout mode)

Select mode tells the assistant what you mean. Layout mode needs no assistant:
drag a widget's corner, and on release the dev runner writes the new `width` /
`height` / `size` into the call that built it; drag its body along a `Column`
or `Row`, and the runner moves it in the `children` list; drag it onto another
container, and the runner moves it into that container's list — or, for a
`Grid`, into the cell under the pointer. Hot reload applies the edit.

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+E` | Enter layout mode (`Cmd+Shift+E` on macOS). Inside select mode it switches directly, keeping your designations as `Enter` would; `Ctrl+Shift+C` switches back. |
| Hover | The widget under the cursor gets teal corner brackets and a caption naming it. A label or icon a widget draws for itself counts as that widget. |
| Click | Select it. `↑` / `↓` then move to its parent and back, for when the container is what you want to resize. The selection holds while the pointer stays on it — over its children too — and moving off it returns to hover. |
| Drag a corner bracket | Resize. A dashed **ghost** follows the pointer, captioned with the value that will be written. |
| Drag the body | Reorder among its siblings, or move it into the container under the pointer. The container it would land in — its own, or another under the pointer — is **tinted**, and an **insertion line** marks the slot, captioned with the sibling it goes before. In a `Grid` the **cell** under the pointer is tinted instead, captioned with its row and column, or its area name, and with whoever already sits there. |
| Release | Write and reload. The ghost stays until the reload lands. |
| `Alt` while dragging | Land on the exact pixel count instead of snapping. |
| `Ctrl+Z` | Undo the last edit this mode wrote. |
| `Esc` | Cancel the drag in flight; otherwise leave. |

The value written is one of the three sizes a widget accepts:

- `"auto"` when you release within a few pixels of the widget's natural size;
- `"wt"` when you release where a weight would put it — the full cross axis of
  a `Column`, or its share of the leftover on the main axis;
- the integer otherwise.

The caption says which (`w 240  ·  h auto`). A widget with a `size` parameter
(`Icon`) stays square: the larger of the two deltas wins.

When one call builds many widgets — a helper returning a card, called from a
loop — every one of them gets a ghost and the caption counts them
(`14 widgets`), because the edit changes them all.

Some drags are **refused**: the corner badge says why, and the file is left
alone. That happens for:

- Resize
  - a size bound to a name or an expression (`width=self.card_w`);
  - a widget whose constructor takes no `width`, `height` or `size`;
- Reorder
  - a reorder whose order is not in one list literal in the file — `head +
    tail`, `[first, *rest]`, a filtered comprehension, items from a call or a
    view model, a name that is assigned twice or used again after its list. The
    badge names the list;
  - a reorder inside a `Stack`, whose children have no order; the badge says so
    while you drag, and the child can still be dropped in another container;
  - a move out of, or into, a container whose `children` are not written as a
    list literal — `Column.builder()`, a `ForEach`, a comprehension. The badge
    says so while you hover, before you release;
  - a `GridItem` whose `row` / `column` or area name is bound to a name or an
    expression; it can neither change cell nor leave the grid;
  - a move into a `Grid` written as a bare `Grid(...)` in a module that does
    not import `GridItem`: the runner adds no import, so the badge asks for
    one;
- Either
  - a call the runner cannot find at the recorded line, or a widget built with
    no source recorded.

Other drags are not refused but simply **do nothing** — no badge, because no
line was ever drawn to promise a change:

- Reorder
  - releasing the widget in its own slot, or its own grid cell;
  - a body drag across the axis — sideways in a `Column`, up or down in a
    `Row`. Only travel along the axis reorders; in a `Flow` or `UniformFlow` any
    direction does;
  - releasing over a `Grid`'s padding, where there is no cell.

After the reload, the badge also reports a size that did not land where the
ghost said, a reload that failed on the edit, or a `"wt"` whose meaning
changed with the move — a share of the `Row`'s leftover where it filled the
`Column`'s width. A widget leaving a `Grid` leaves its `GridItem` behind, and
the badge names the `width` / `height` / `padding` / `alignment` the item
carried, since those stay with it. Either way `Ctrl+Z` still reverts it —
unless you have edited that line by hand since, in which case the undo is
refused rather than applied to the wrong text.

Only `width`, `height`, `size`, the place of a child in the list that orders
the children — `children=[...]`, or the data a comprehension or
`Column.builder()` iterates, even one bound to a name (`tags = [...]`) — and
a `GridItem`'s `row` / `column` or area, added or removed with the wrapper
itself as a widget enters or leaves a `Grid`, are ever written. `padding`,
`gap`, colours and every other style value are yours to change in code.

## Jump to the source

`Ctrl+Shift+Click` (`Cmd+Shift+Click` on macOS) on a widget **opens the code
that built it**, in your editor. It is not a mode: it works with no mode on, and
inside select mode or layout mode, where it opens the code instead of
designating or selecting — so you can read through several widgets without
leaving marks behind.

Hold `Ctrl+Shift` and the widget under the cursor gets **rose** brackets and a
caption naming its file and line, so you can aim before clicking — a different
colour from select mode's amber, so inside that mode you can tell a jump from
a designation. After the click a
caption says what happened — `opening app.py:42`, or why nothing did — and
clears on the next pointer move.

VS Code works as installed. For another editor, pass its URL scheme to
`--editor` — `{file}` and `{line}` are filled in for you, encoding and all:

```bash
python -m nuiitivet.dev run app.py --editor "cursor://file{file}:{line}:1"
python -m nuiitivet.dev run app.py \
  --editor "jetbrains://pycharm/navigate/reference?project=NAME&path={file}:{line}"
```

`Ctrl+Shift` is the dev runner's prefix: every chord it claims — `Ctrl+Shift+C`,
`Ctrl+Shift+E`, `Ctrl+Shift+Click` — starts with it, and nothing else does.

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

These markers are **indigo**; select mode's are **amber**; layout mode's ghosts
are **teal**; the source jump's brackets are **rose**. What the assistant did,
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

## See also

- [AI pair-programming](index.md) — the full edit → see → act loop
  this bridge is one half of.
- [Hot Reload](hot_reload.md) — the other half: how saves rebuild the running
  tree.
- [The `nuiitivet-debug` skill](nuiitivet_debug_skill.md) — the skill that teaches
  an assistant to use these tools well.
