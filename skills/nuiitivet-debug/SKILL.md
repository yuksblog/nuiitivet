---
name: nuiitivet-debug
description: Run, hot-reload, inspect, drive, and debug a running Nuiitivet app. Covers launching under hot reload (`python -m nuiitivet.dev`) and the dev bridge / MCP server that lets an assistant check and drive the live app (`status`, `describe_tree`, `describe_state`, `reload_log`, `interaction_log`, `runtime_log`, `screenshot`, `click`, `type`, `key`, `wait_for`). Use whenever there is a Nuiitivet app to run, verify, or debug — the see → act → verify half of the loop. To *write* the widget code, use the nuiitivet-app skill.
---

# Running & Debugging Nuiitivet Apps

The **nuiitivet-app** skill makes the assistant *write* correct Nuiitivet code.
This skill is the other half: *run* that code under hot reload, then *see* → *act*
→ *verify* against the live app.

## The loop

Once set up, the working loop is:

**edit (hot reload) → see (`status`, then `describe_tree` / `describe_state`) → act
(`click` / `type` / `key`, then `wait_for`) → verify → edit.**

The sections below map to it: a one-time **Setup**, then **Edit / See / Act /
Verify**. The nuiitivet-app skill keeps *edit* producing correct widgets; this
skill keeps *see / act / verify* fast and reliable.

## Setup — before the loop

Two one-time steps get you into the loop; you then cycle without repeating them.

### Launch under hot reload

Nuiitivet apps are developed under in-process hot reload: edit a widget, save, and
the running window updates **while `Observable` state survives**. Launch for
development with the dev runner:

```
python -m nuiitivet.dev path/to/app.py      # or: --module pkg.app
```

Production launch (`App.run()`) is unchanged; hot reload is a development-time
wrapper.

**Hot reload requires a factory root.** It works **only if the app root is a
factory** — a zero-argument callable returning the root widget — passed to
`App(content=...)` *without* calling it. What depends on it:

- **Pass a factory, not an instance.** `App(content=build_root())` (with the call)
  yields a widget instance the reloader cannot rebuild, so hot reload stops
  applying your edits. A `Widget` *subclass* works directly
  (`App(content=Counter)`); a factory needing arguments closes over them
  (`App(content=lambda: Home(cfg))`).
- **Per-tree init goes in the factory / widget `__init__`, not `main()`.**
  `main()` runs **once** at startup and never again on reload; side effects and
  module-level state created there are not restored.

If a reload seems to do nothing or the app resets its state on every edit, suspect
a stray `content=build_root()` first.

### Register the dev bridge / MCP server

The dev bridge lets an assistant inspect and drive the running app. Register it
once in your MCP host:

```
python -m nuiitivet.dev mcp        # needs: pip install 'nuiitivet[mcp]'
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
| Is the reactive state as intended? | `describe_state` — the live `Observable` values behind the tree |
| My `click` / `type` / `key` had no visible effect — why? | `runtime_log` — a swallowed callback exception, or an uncaught background/async error (the app stays alive but the handler raised); also WARNING+ output. If a repeated failure is collapsed to one line, `set_runtime_log_verbose(True)` shows every occurrence |
| Did the last edit reload cleanly, and which file changed? | `reload_log` — recent hot-reload outcomes; `changed` pinpoints the edited module(s), an `error` outcome means the save didn't compile and the live UI is stale |
| What did the human do in the app between my turns? | `interaction_log` — their recent clicks / keys / text markers, so you re-sync instead of acting on a stale screen |
| A **human reported** a visual problem AND tree + state don't explain it? | first re-check `describe_tree`, then `describe_state`; **only if the cause still isn't clear**, `screenshot` — reach for it only because a human reported the problem |

### Blind spots

Read these tools' output as *what was recorded or built*, not as *what happened or
is on screen*:

- **`describe_tree` is structure, not rendering or visibility.** Inactive `Deck`
  pages, overlays, and z-order are all listed as-is, so the tree alone can't say
  which one is on screen. Decide the visible page from `describe_state` — a
  `Deck`'s selected index shows up there, joined against the child order in the
  tree.
- **A node's `rect` can read `0` or stale right after a measurement.** Never
  diagnose a layout bug from a single `rect` value; re-observe after things
  settle.

## Act — drive the running app

`click`, `type`, `key` drive the app. Resolve targets from `describe_tree`, or by
a stable `key`.

**Make a widget targetable — `keyed()`.** Attach a stable `key` with the `keyed()`
modifier so the bridge can drive the widget by `key`, and so its state survives a
reorder across hot reload:

```python
widget.modifier(keyed("increment-btn"))
```

Add it on demand and remove it once the need is gone. When chained with wrapping
modifiers, apply `keyed()` **last**.

A returned node is **not** proof the intended handler fired. `click` resolves the
first depth-first match, then dispatches at that node's center — so a duplicate
`label` can resolve to the wrong (or a non-interactive) node and come back looking
successful while the screen does nothing. Prefer a `key` when a label repeats; if
there is none, coordinate-target the center of the node's `describe_tree` `rect`.
Then confirm the effect in **Verify** — never the return alone.

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
  proof the handler fired. Re-observe `describe_tree` / `describe_state` (after
  `wait_for` settles any async work) and confirm the state actually changed.
