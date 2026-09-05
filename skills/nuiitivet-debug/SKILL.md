---
name: nuiitivet-debug
description: Run, hot-reload, inspect, drive, and debug a running Nuiitivet app. Covers launching under hot reload (`python -m nuiitivet.dev`) and the dev bridge / MCP server that lets an assistant check and drive the live app (`status`, `describe_tree`, `describe_state`, `describe_selection`, `reload_log`, `interaction_log`, `runtime_log`, `screenshot`, `click`, `scroll`, `scroll_into_view`, `type`, `key`, `wait_for`, `profile_start`, `profile_stop`). Use whenever there is a Nuiitivet app to run, verify, or debug — the see → act → verify half of the loop. When the user refers to a "selection" (e.g. "selection 1", "the selected widget"), it means widgets picked in the running app — read it with `describe_selection` first. To *write* the widget code, use the nuiitivet-app skill.
---

# Running & Debugging Nuiitivet Apps

The **nuiitivet-app** skill makes the assistant *write* correct Nuiitivet code.
This skill is the other half: *run* that code under hot reload, then *see* → *act*
→ *verify* against the live app.

## The loop

Once set up, the working loop is:

**edit (hot reload) → see (`status`, then `describe_tree` / `describe_state`) → act
(`click` / `scroll` / `type` / `key`, then `wait_for`) → verify → edit.**

The sections below map to it: a one-time **Setup**, then **Edit / See / Act /
Verify**. The nuiitivet-app skill keeps *edit* producing correct widgets; this
skill keeps *see / act / verify* fast and reliable.

## Setup — before the loop

Two one-time steps get you into the loop; you then cycle without repeating them.

### Launch under hot reload

**Call `status` first.** The human usually has the app open already; `running:
true` means use that process (check `title`), and a second launch would put a
second window on their screen. Launch only on a "no running app" error:

```
python -m nuiitivet.dev run path/to/app.py  # or: run --module pkg.app
python -m nuiitivet.dev run app.py -- --flag value  # args for the app's own entry
```

The app's `sys.argv` is its path plus anything after `--` — the runner's own
arguments never reach it.

Under the dev runner, saving a widget edit updates the running window **while
`Observable` state survives**.

Production launch (`App.run()`) is unchanged; hot reload is a development-time
wrapper.

**Hot reload requires a factory root.** It works **only if the window's root is
a factory** — a zero-argument callable returning the root widget — passed to
`Window(content=...)` *without* calling it (the entry point is
`nv.App(nv.Window(content=...))`). What depends on it:

- **Pass a factory, not an instance.** `Window(content=build_root())` (with the
  call) yields a widget instance the reloader cannot rebuild, so hot reload stops
  applying your edits. A `Widget` *subclass* works directly
  (`Window(content=Counter)`); a factory needing arguments closes over them
  (`Window(content=lambda: Home(cfg))`).
- **Per-tree init goes in the factory / widget `__init__`, not `main()`.**
  `main()` runs **once** at startup and never again on reload; side effects and
  module-level state created there are not restored.

If a reload seems to do nothing or the app resets its state on every edit, suspect
a stray `content=build_root()` first.

### Register the dev bridge / MCP server

The dev bridge lets an assistant inspect and drive the running app. Register it
once in your MCP host:

```
python -m nuiitivet.dev mcp        # needs: pip install 'nuiitivet[dev]'
```

It is **development-only** and forwards to the running dev process (the one
started with `python -m nuiitivet.dev`).

## Edit — change a widget under hot reload

Write or change the widget with the **nuiitivet-app** skill's idioms, then save:
the running window reloads in place while `Observable` state survives — no restart,
no lost state. Confirm the reload actually landed in **Verify**. If the window
doesn't update or resets its state on every save, it is the factory contract — see
**Launch under hot reload**.

## See — check the running app

Match the question you actually have to the one tool that answers it. This is a
**reverse lookup, not a sequence** — reach only for the row you need, never run it
top to bottom.

| The question you have | Tool |
| --- | --- |
| Is the app up and running? | `status` — liveness, title, last-reload outcome, error count, a `blank` flag for a white screen |
| Is the widget tree built as intended? | `describe_tree` — the structure, and how you resolve action targets |
| Is a control disabled, selected, or focused — and did my `type` land? | `describe_tree` — each node's `state` map. `disabled` / `focused` / `selected` appear only when true; `value` appears whenever the widget has one, and carries a toggle's checked state (a tri-state checkbox reports `null`, a range slider a `[start, end]` pair) |
| Is the reactive state as intended? | `describe_state` — the live `Observable` values behind the tree, named as the widget bound them (`_state_internal`, `checked_external_tri`), so they differ per widget; read `describe_tree`'s `state` for the same facts in one vocabulary. Animation state is omitted by default; pass `include_animations=True` when an animation itself is the bug |
| My `click` / `scroll` / `type` / `key` had no visible effect — why? | `runtime_log` — a swallowed callback exception, or an uncaught background/async error (the app stays alive but the handler raised); also WARNING+ output. If a repeated failure is collapsed to one line, `set_runtime_log_verbose(True)` shows every occurrence |
| Did the last edit reload cleanly, and which file changed? | `reload_log` — recent hot-reload outcomes; `changed` pinpoints the edited module(s), an `error` outcome means the save didn't compile and the live UI is stale |
| What did the human do in the app between my turns? | `interaction_log` — their recent clicks / keys / text markers / scrolls, plus `window_opened` / `window_closed` lifecycle events, so you re-sync instead of acting on a stale screen |
| The human says "this is wrong" / "look at this part" without naming a widget? | `describe_selection` — they may have already pointed at it in inspect mode. Check before guessing from a screenshot |
| `status` reports a `selection` whose `seq` you haven't seen? | `describe_selection` — they designated something for you since your last turn |
| A **human reported** a visual problem AND tree + state don't explain it? | first re-check `describe_tree`, then `describe_state`; **only if the cause still isn't clear**, `screenshot` — reach for it only because a human reported the problem |
| A **human reported** jank or slowness ("this screen stutters", "typing feels heavy")? | `profile_start` → reproduce the interaction (drive it, or ask the human to) → `profile_stop` — reach for it only because a human reported it; you cannot perceive jank or excess rebuilds yourself. The report's `rebuilds` and `bindings` counters name the widget doing wasted work; `frames` carries paint-walk mean/p95/max ms. Recording slows frames ~10%, so stop it when done. Paint counts equal painted-frame count (every painted frame walks the whole tree) — read `rebuilds`/`bindings` for the per-widget signal |

**Multiple windows.** `status` lists every open window (`id`, `title`,
`main`/`focused` flags). Every tree/state/action tool takes `window=<id>`;
omitted, it targets the **main** window — not the focused one — so a secondary
window is only reached by passing its id explicitly. An action on a window
blocked by a modal child fails with an error naming the blocking window; drive
the modal child (or close it) instead of retrying. Window ids are never reused,
so an id from an earlier `status` stays valid for that window's lifetime.
Inspect mode and the interaction log cover every window, and a designated
node's `describe_selection` payload names its window (`"window": <id>`) — use
that id for the follow-up `describe_tree` / action calls.
`interaction_log` also records window lifecycle: `window_opened` /
`window_closed` events carry `window` (`{"id", "title", "main"}`) and cover
every path — an OS-title-bar close or a parent-cascade close appears there even
though no click does. A `window_closed` for an id you remembered means that id
is stale; re-run `status` before addressing it.

### Reading a designation

`describe_selection` is the one channel that runs **from the human to you** —
what they *meant*, not what the app is.

- Read a node's `tree` / `state` (both scoped to it) instead of dumping the whole
  tree. `key` / `label` drive it; `path` locates it in `describe_tree`.
- **No `key`, `label`, or `target` on it?** Expected — most apps pass no
  `key=`, and then `resolve_target` has nothing to anchor on. Its scoped
  `tree` is what tells two same-typed nodes apart (two bare `_RailItemButton`s by
  the `Text` inside each), and `path` is how you reach it.
- A node's `rect` here is what is **on screen** of it, clips applied — unlike
  `describe_tree`'s. A node clipped away entirely reports no `rect` at all.
- **`source` is the line that built it** — edit there instead of searching.
  Innermost first; the `target: true` frame is the construction site, and the
  rest are its callers, so a widget built by a shared helper shows both "change
  every one" and "change this one" and *what the human said* picks. Absent when
  the runner is not recording sites.
- Refer to a designation by its `index`: it matches the badge on their screen.
- `lost` > 0 — some designations did not survive a reload. **Say so.** Never
  reason over a silently shortened list.
- `active: true` — they are still in inspect mode and have not pressed `Enter`,
  so the set is not committed. Do not act on it: tell them that, or ask them to
  press `Enter`.
- `regions` are areas, numbered in the same sequence as `nodes`:
  - `container` is the widget enclosing the box; `contents` is a nested tree of
    what the box crosses, tagged `contained` / `clipped` (no tag = only on the
    path to a match).
  - One box, two meanings — "the gap between these things" (`container`) or
    "these things" (`contents`). Nothing is collapsed for you; pick from what the
    human said.
  - Empty `contents` is an answer, not a miss: nothing is painted there, and
    `container` names what should have been.
  - Re-derived on every call, so read one again after your fix.
- You cannot arm it and cannot clear it. If nothing is designated, ask them to
  press `Ctrl+Shift+C`, click a widget or drag a box over the area, then `Enter`.

### Blind spots

Read these tools' output as *what was recorded or built*, not as *what happened or
is on screen*:

- **`describe_tree` is structure, not rendering or visibility.** Inactive `Deck`
  pages, overlays, and z-order are all listed as-is, so the tree alone can't say
  which one is on screen. Decide the visible page from `describe_state` — a
  `Deck`'s selected index shows up there, joined against the child order in the
  tree.
- **`focused` sits on the node that actually holds the focus, which may be a
  child.** `nv.TextField` delegates to the `EditableText` inside it, so the flag
  lands there and not on the `TextField` you targeted. Search the subtree for it.
- **A node's `rect` can read `0` or stale right after a measurement.** Never
  diagnose a layout bug from a single `rect` value; re-observe after things
  settle.
- **`rect` is content space, not screen space.** Inside a scrolled region it does
  *not* subtract the scroll offset, so a listed node may be nowhere on screen and
  a `rect` is never evidence a widget is visible. Target it by `key` / `label`
  and let the bridge resolve the real position; coordinate-targeting from a
  `rect` inside a scroll region is wrong by exactly the offset.
- **`screenshot` re-renders the tree offscreen instead of capturing the
  window.** It can come back clean while the screen is visibly broken (GPU path,
  swap chain), so never dismiss a human's visual report on that basis — ask them
  for their own screenshot.

## Act — drive the running app

`click`, `scroll`, `scroll_into_view`, `type`, `key` drive the app. Resolve
targets from `describe_tree`, or by a stable `key`.

**Make a widget targetable — `key=`.** Every widget takes a stable `key` in its
constructor so the bridge can drive it by `key`, and so its state survives a
reorder across hot reload:

```python
nv.Button("increment", key="increment-btn")
```

Add it on demand and remove it once the need is gone. For a widget built by a
helper you do not control, assign the public attribute: `widget.key = "row"`.

A returned node is **not** proof the intended handler fired. `click` resolves the
first depth-first match, then dispatches at that node's center — so a duplicate
`label` can resolve to the wrong (or a non-interactive) node and come back looking
successful while the screen does nothing. Prefer a `key` when a label repeats; if
there is none, coordinate-target the center of the node's `describe_tree` `rect`.
Then confirm the effect in **Verify** — never the return alone.

### Editing a text field — `type` inserts, `key` edits

`type` only ever inserts. To delete what it inserted, or to move the caret, use
`key` with an editing key: `backspace`, `delete`, `left`, `right`, `home`,
`end`. Pass `modifiers=["shift"]` with one to extend the selection instead of
moving — then `type` replaces what is selected. To clear a field, select it all
with `key a modifiers=["accel"]` and then `key backspace`; there is no
"set the text" verb.

### Off-screen targets — `scroll_into_view`, then `scroll`

An action on a widget scrolled out of its region — or covered by a modal —
**fails** with a "not visible" error instead of dispatching where it would hit
something else. Not a bad target: the widget exists, it just isn't reachable yet.

- **`scroll_into_view(key=…)` is the fix** — one call, exact offset, and the
  retried `click` lands. Reach for it whenever you know which widget you want.
- **`scroll` is for exploring** a list you haven't read yet. **Target the region,
  not a row in it**: a row anchor is refused, because the wheel would carry it
  off screen and leave your next call with no target. Regions often have no
  `key` — give the region one with `key=`, or use the `x` / `y` centre of the region's
  rect, which stays put as the content scrolls. `dx` / `dy` are **wheel notches,
  ~20 px each**, positive = down / right.
- **Read the result.** `at_end: true` with an unchanged `offset` is your stop
  condition — without it a scroll-until-found loop never ends. `handled: false`
  means your coordinates hit no scrollable region.

### `wait_for` — settle before you observe

After an action that starts async work (network, a timer, an animation), call
`wait_for` — naming a `key` / `label` / `text` condition, or `present=False` to
wait one *out* — before `describe_tree`, so you read the settled state instead of
a still-loading one.

- **Waiting on async work:** `wait_for` blocks your turn synchronously for up to
  `timeout` (default 3s). That fits app-driven settling.
- **Waiting on a *human*** (someone deciding when to click): do **not** set one
  long `timeout` on it. Keep each `wait_for` short and poll in a loop — re-issue
  it, checking `interaction_log` between tries. The condition is detected only if it
  becomes true while a `wait_for` call is actively running, and one long call blocks
  the whole turn.

## Verify — confirm the change

Don't trust a green return or a single number; confirm against the live app.

- **The edit landed.** `reload_log` shows a `success` outcome with your file in
  `changed`. An `error` outcome means the save didn't compile and the live UI is
  stale — fix and re-save before reading anything else.
- **No new error appeared — check `runtime_log`, not `error_count`.** `error_count`
  (from `status`) is cumulative and a green build does not reset it, so a clean
  `last_reload: success` can still report failures from *before* your fix. Instead,
  note the newest `runtime_log` seq before you edit; after the reload, check whether
  any ERROR with a *higher* seq appeared. (`runtime_log` and `reload_log` seqs are
  separate counters — don't compare across them.)
- **The effect happened, not just the return.** A `{"clicked": …}` return is not
  proof the handler fired (a `{"scrolled": …}` with `handled: false` is not even
  proof anything moved). Re-observe `describe_tree` / `describe_state` (after
  `wait_for` settles any async work) and confirm the state actually changed.
