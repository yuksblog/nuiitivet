---
name: nuiitivet-debug
description: Run, hot-reload, inspect, drive, and debug a running Nuiitivet app. Covers launching under hot reload (`python -m nuiitivet.dev`), the factory contract that keeps reload working, and the dev bridge / MCP server that lets an assistant check and drive the live app (`status`, `describe_tree`, `describe_state`, `reload_log`, `interaction_log`, `runtime_log`, `screenshot`, `click`, `type`, `key`, `wait_for`). Use whenever there is a Nuiitivet app to run, verify, or debug — the see → act → verify half of the pair-programming loop. To *write* the widget code, use the nuiitivet-app skill.
---

# Running & Debugging Nuiitivet Apps

The **nuiitivet-app** skill makes the assistant *write* correct Nuiitivet code.
This skill is the other half: *run* that code under hot reload, *see* what the
running app is doing, *act* on it, and *verify* the result. Together they form the
loop **edit (hot reload) → see → act → verify → edit**.

## Launch under hot reload

Nuiitivet apps are developed under in-process hot reload: edit a widget, save, and
the running window updates **while `Observable` state survives**. Launch for
development with the dev runner:

```
python -m nuiitivet.dev path/to/app.py      # or: --module pkg.app
```

Production launch (`App.run()`) is unchanged; hot reload is a development-time
wrapper.

### The factory contract (why rule 6 exists)

Hot reload works **only if the app root is a factory** — a zero-argument callable
returning the root widget — passed to `App(content=...)` *without* calling it.
This is core rule 6 of the nuiitivet-app skill; here is what depends on it:

- **Pass a factory, not an instance.** `App(content=build_root())` (with the
  call) yields a widget instance the reloader cannot rebuild — hot reload goes
  inert. A `Widget` *subclass* works directly (`App(content=Counter)`); a factory
  needing arguments closes over them (`App(content=lambda: Home(cfg))`).
- **Per-tree init goes in the factory / widget `__init__`, not `main()`.**
  `main()` runs **once** at startup and never again on reload; side effects and
  module-level state created there are not restored.

If a reload seems to do nothing or the app resets its state on every edit, suspect
a stray `content=build_root()` first.

## The dev bridge / MCP server — see & act

The dev bridge lets an assistant inspect and drive the running app. Register it
once in your MCP host:

```
python -m nuiitivet.dev mcp        # needs: pip install 'nuiitivet[mcp]'
```

It is **development-only** and forwards to the running dev process (the one
started with `python -m nuiitivet.dev`).

### Checking the app — look up by question

Match the question you actually have to the one tool that answers it. This is a
**reverse lookup, not a sequence** — reach only for the row you need, never run it
top to bottom.

| The question you have | Tool |
| --- | --- |
| Is the app up and running? | `status` — liveness, title, last-reload outcome, error count, a `blank` flag for a white screen |
| Is the widget tree built as intended? | `describe_tree` — the structure, and how you resolve action targets |
| Is the reactive state as intended? | `describe_state` — the live `Observable` values behind the tree |
| My `click` / `type` / `key` had no visible effect — why? | `runtime_log` — a swallowed callback exception, or an uncaught background/async error (the app stays alive but the handler raised); also WARNING+ output |
| Did the last edit reload cleanly, and which file changed? | `reload_log` — recent hot-reload outcomes; `changed` pinpoints the edited module(s), an `error` outcome means the save didn't compile and the live UI is stale |
| What did the human do in the app between my turns? | `interaction_log` — their recent clicks / keys / text markers, so you re-sync instead of acting on a stale screen |
| A visual problem was reported and tree + state don't explain it? | first re-check `describe_tree`, then `describe_state`; **only if the cause still isn't clear**, `screenshot` (pixels — image tokens are expensive) |

The first three answer almost everything about *your own* changes — "did it
start", "did my change land", "is the value right". The `*_log` tools cover what
happened **outside your turn or silently**: `runtime_log` when an action seems to
do nothing (a handler raised), and `reload_log` / `interaction_log` to catch edits
or clicks the human made while you worked — either makes your last `describe_tree`
stale. (If a repeated failure is collapsed in `runtime_log`, call
`set_runtime_log_verbose(True)` to see every occurrence.) `screenshot` stays the
genuine last resort: even for a reported visual bug, confirm tree and state first
— the cause is usually there, not the pixels.

### Acting

`click`, `type`, `key` drive the app. Resolve targets from `describe_tree`, or by
a stable `key` (see below).

### `wait_for` — settle before you observe

After an action that starts async work (network, a timer, an animation), call
`wait_for` — naming a `key` / `label` / `text` condition, or `present=False` to
wait one *out* — before `describe_tree`, so you observe the settled state instead
of racing a spinner.

- **Waiting on async work:** `wait_for` blocks your turn synchronously for up to
  `timeout` (default 3s). That fits app-driven settling.
- **Waiting on a *human*** (someone deciding when to click): do **not** park one
  long `timeout` on it. Keep each `wait_for` short and poll in a loop — re-issue
  it, checking `interaction_log` between tries. The condition must land inside a
  call's live window to be seen, and a single long block ties up the turn.

## Make a widget targetable — `keyed()`

Attach a stable `key` with the `keyed()` modifier so the bridge can drive the
widget by `key`, and so its state survives a reorder across hot reload:

```python
widget.modifier(keyed("increment-btn"))
```

Add it on demand and remove it once the need is gone. When chained with wrapping
modifiers, apply `keyed()` **last**.

## The loop

With the app launched and the bridge registered, the working loop is:

**edit (hot reload) → see (`status`, then `describe_tree` / `describe_state`) →
act (`click` / `type` / `key`, then `wait_for`) → verify → edit.**

The nuiitivet-app skill keeps the *edit* step producing correct widgets; this
skill keeps the *see / act / verify* steps cheap and reliable.
